"""
按 ENTITY_SYNC_TABLES 将达梦表只读同步到 Qdrant 实体集合。
"""

from __future__ import annotations

import logging
import threading
from datetime import UTC, datetime
from typing import Any

from app.config import settings
from app.infrastructure.db import dameng_readonly as dm
from app.infrastructure.vector.entity_store import EntityVectorStore
from app.sync.entity_mapper import map_row_to_entity
from app.sync.entity_sync_status import table_to_stream_name, upsert_entity_sync_checkpoint
from app.sync.table_config import parse_entity_sync_tables

logger = logging.getLogger(__name__)

_sync_lock = threading.Lock()

# 行内常见更新时间 / 主键列（小写）；仅用于推进 Agent Postgres 水位线，不写达梦
_WATERMARK_TS_KEYS = (
    "update_time",
    "updated_at",
    "gmt_modified",
    "modify_time",
    "last_update_time",
)
_WATERMARK_ID_KEYS = ("id", "device_id", "deviceid", "pk_id")


def _iso_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _pick_row_value(row: dict[str, Any], keys: tuple[str, ...]) -> Any:
    lower_map = {str(k).lower(): v for k, v in row.items()}
    for key in keys:
        if key in lower_map and lower_map[key] is not None:
            return lower_map[key]
    return None


def _advance_watermark_from_rows(
    rows: list[dict[str, Any]],
    *,
    current_ts: str | None,
    current_id: str | None,
) -> tuple[str | None, str | None]:
    """从本页行推进水位（取更大的时间戳 / id 字符串）。"""
    best_ts = current_ts
    best_id = current_id
    for row in rows:
        raw_ts = _pick_row_value(row, _WATERMARK_TS_KEYS)
        if raw_ts is not None:
            text = str(raw_ts).strip()
            if text and (best_ts is None or text > best_ts):
                best_ts = text
        raw_id = _pick_row_value(row, _WATERMARK_ID_KEYS)
        if raw_id is not None:
            text = str(raw_id).strip()
            if text and (best_id is None or text > best_id):
                best_id = text
    return best_ts, best_id


def is_entity_sync_running() -> bool:
    """是否有同步任务持有锁（非阻塞探测）。"""
    acquired = _sync_lock.acquire(blocking=False)
    if acquired:
        _sync_lock.release()
        return False
    return True


def run_entity_sync(*, tables_override: str | None = None) -> dict[str, Any]:
    """
    执行一次实体同步。

    返回结构供 API / 前端展示：skipped、missing_tables、tables[]、upserted 等。
    """
    if not _sync_lock.acquire(blocking=False):
        return {
            "ok": False,
            "skipped": True,
            "reason": "sync_in_progress",
            "message": "已有同步任务进行中，请稍后再试",
            "missing_tables": [],
            "tables": [],
            "upserted": 0,
        }

    try:
        return _run_entity_sync_unlocked(tables_override=tables_override)
    finally:
        _sync_lock.release()


def _run_entity_sync_unlocked(*, tables_override: str | None = None) -> dict[str, Any]:
    raw_cfg = tables_override if tables_override is not None else settings.entity_sync_tables
    plan = parse_entity_sync_tables(raw_cfg)
    if plan.skip:
        return {
            "ok": True,
            "skipped": True,
            "reason": "empty_config",
            "message": "ENTITY_SYNC_TABLES 为空，未执行任何表数据转换",
            "missing_tables": [],
            "tables": [],
            "upserted": 0,
            "config": raw_cfg or "",
        }

    dm.assert_dm_read_only_config()
    if not dm.is_dm_configured():
        return {
            "ok": False,
            "skipped": True,
            "reason": "dm_not_configured",
            "message": "未配置达梦连接（DM_HOST / DM_USER / DM_PASSWORD）",
            "missing_tables": [],
            "tables": [],
            "upserted": 0,
        }

    if not (settings.qdrant_url or "").strip():
        return {
            "ok": False,
            "skipped": True,
            "reason": "qdrant_not_configured",
            "message": "未配置 QDRANT_URL，无法写入向量库",
            "missing_tables": [],
            "tables": [],
            "upserted": 0,
        }

    try:
        available = dm.list_user_tables()
    except dm.DamengReadOnlyError as exc:
        return {
            "ok": False,
            "skipped": True,
            "reason": "dm_connect_error",
            "message": str(exc),
            "missing_tables": [],
            "tables": [],
            "upserted": 0,
            "config": raw_cfg or "",
        }
    missing: list[str] = []
    targets: list[str] = []

    if plan.all_tables:
        targets = list(available)
    else:
        for name in plan.explicit_tables:
            resolved = dm.resolve_table_name(name, available)
            if resolved is None:
                missing.append(name)
            else:
                targets.append(resolved)

    store = EntityVectorStore()
    table_results: list[dict[str, Any]] = []
    total_upserted = 0
    page_size = max(1, int(settings.entity_sync_max_rows_per_table))

    for table in targets:
        stream = table_to_stream_name(table)
        try:
            rows_read = 0
            table_upserted = 0
            page_no = 0
            offset = 0
            watermark_ts: str | None = None
            watermark_id: str | None = None

            while True:
                rows = dm.fetch_table_rows(table, limit=page_size, offset=offset)
                if not rows:
                    break

                entities: list[dict[str, Any]] = []
                for idx, row in enumerate(rows):
                    mapped = map_row_to_entity(table, row, rows_read + idx)
                    entities.append(mapped)

                count = store.upsert_entities(entities)
                rows_read += len(rows)
                table_upserted += count
                total_upserted += count
                watermark_ts, watermark_id = _advance_watermark_from_rows(
                    rows,
                    current_ts=watermark_ts,
                    current_id=watermark_id,
                )
                offset += len(rows)
                page_no += 1

                if len(rows) < page_size:
                    break

            table_results.append(
                {
                    "table": table,
                    "rows_read": rows_read,
                    "upserted": table_upserted,
                    "ok": True,
                    "error": None,
                    "truncated": False,
                    "pages": page_no,
                }
            )
            # 水位线只写 Agent Postgres；禁止在达梦落同步标记
            upsert_entity_sync_checkpoint(
                stream,
                watermark_ts=watermark_ts or _iso_now(),
                watermark_id=watermark_id,
                last_full_at=_iso_now(),
                last_ok=True,
                last_rows_read=rows_read,
                last_upserted=table_upserted,
                last_error=None,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("同步表失败 table=%s", table)
            table_results.append(
                {
                    "table": table,
                    "rows_read": 0,
                    "upserted": 0,
                    "ok": False,
                    "error": str(exc),
                    "truncated": False,
                }
            )
            upsert_entity_sync_checkpoint(
                stream,
                last_full_at=_iso_now(),
                last_ok=False,
                last_rows_read=0,
                last_upserted=0,
                last_error=str(exc),
            )

    ok_flag = all(bool(t["ok"]) for t in table_results) if table_results else not bool(missing)

    message_parts: list[str] = []
    if missing:
        message_parts.append(f"以下表不存在已跳过：{', '.join(missing)}")
    synced = [t["table"] for t in table_results if t["ok"]]
    if synced:
        message_parts.append(f"已转换：{', '.join(synced)}（共写入 {total_upserted} 条）")
    failed = [t["table"] for t in table_results if not t["ok"]]
    if failed:
        message_parts.append(f"失败：{', '.join(failed)}")
    if not targets and missing:
        message_parts.append("没有可转换的表")
    if plan.all_tables and not targets:
        message_parts.append("库中未发现可转换的表")

    return {
        "ok": ok_flag,
        "skipped": False,
        "reason": None,
        "message": "；".join(message_parts) or "同步完成",
        "missing_tables": missing,
        "tables": table_results,
        "upserted": total_upserted,
        "config": raw_cfg or "",
        "collection": settings.qdrant_collection_entities,
    }
