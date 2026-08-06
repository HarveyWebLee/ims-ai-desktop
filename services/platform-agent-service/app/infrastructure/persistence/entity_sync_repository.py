"""实体同步状态与水位线仓储：内存主缓存 + 可选 Postgres 双写（禁达梦写标记）。"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

_pool: Any | None = None
_last_at: str | None = None
_last_result: dict[str, Any] | None = None
_checkpoints: dict[str, dict[str, Any]] = {}


def configure_entity_sync_persistence(pool: Any | None) -> None:
    """注入 Postgres 连接池；None 时仅内存，并清空内存快照。"""
    global _pool, _last_at, _last_result, _checkpoints
    _pool = pool
    if pool is None:
        _last_at = None
        _last_result = None
        _checkpoints.clear()
        return
    _hydrate_from_db()


def _iso_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _row_to_checkpoint(row: dict[str, Any]) -> dict[str, Any]:
    def _ts(value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        text = str(value).strip()
        return text or None

    return {
        "stream_name": str(row.get("stream_name") or ""),
        "watermark_ts": _ts(row.get("watermark_ts")),
        "watermark_id": (str(row["watermark_id"]) if row.get("watermark_id") is not None else None),
        "last_full_at": _ts(row.get("last_full_at")),
        "last_ok": row.get("last_ok"),
        "last_rows_read": int(row.get("last_rows_read") or 0),
        "last_upserted": int(row.get("last_upserted") or 0),
        "last_error": (str(row["last_error"]) if row.get("last_error") is not None else None),
        "updated_at": _ts(row.get("updated_at")),
    }


def _hydrate_from_db() -> None:
    """进程启动时从 Postgres 恢复最近一次结果与水位线。"""
    global _last_at, _last_result, _checkpoints
    if _pool is None:
        return
    try:
        with _pool.connection() as conn:
            status_row = conn.execute(
                "SELECT last_at, last_result FROM entity_sync_status WHERE id = 1"
            ).fetchone()
            cp_rows = conn.execute(
                """
                SELECT stream_name, watermark_ts, watermark_id, last_full_at,
                       last_ok, last_rows_read, last_upserted, last_error, updated_at
                FROM entity_sync_checkpoint
                ORDER BY stream_name
                """
            ).fetchall()
    except Exception:  # noqa: BLE001
        logger.exception("加载 entity_sync 持久化状态失败（保持空快照）")
        return

    if status_row:
        raw_at = status_row.get("last_at") if isinstance(status_row, dict) else None
        if isinstance(raw_at, datetime):
            _last_at = (
                raw_at.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
            )
        elif raw_at is not None:
            _last_at = str(raw_at)
        else:
            _last_at = None
        raw_result = status_row.get("last_result") if isinstance(status_row, dict) else None
        if isinstance(raw_result, dict):
            _last_result = dict(raw_result)
        elif isinstance(raw_result, str) and raw_result.strip():
            try:
                parsed = json.loads(raw_result)
                _last_result = dict(parsed) if isinstance(parsed, dict) else None
            except json.JSONDecodeError:
                _last_result = None
        else:
            _last_result = None

    loaded: dict[str, dict[str, Any]] = {}
    for row in cp_rows or []:
        if not isinstance(row, dict):
            continue
        cp = _row_to_checkpoint(row)
        name = cp["stream_name"]
        if name:
            loaded[name] = cp
    _checkpoints = loaded


def remember_entity_sync_result(result: dict[str, Any]) -> None:
    """记录最近一次同步返回（内存 + 可选 Postgres）。"""
    global _last_at, _last_result
    at = _iso_now()
    payload = dict(result)
    _last_at = at
    _last_result = payload
    if _pool is None:
        return
    try:
        with _pool.connection() as conn:
            conn.execute(
                """
                INSERT INTO entity_sync_status (id, last_at, last_result, updated_at)
                VALUES (1, %s::timestamptz, %s::jsonb, NOW())
                ON CONFLICT (id) DO UPDATE SET
                    last_at = EXCLUDED.last_at,
                    last_result = EXCLUDED.last_result,
                    updated_at = NOW()
                """,
                (at, json.dumps(payload, ensure_ascii=False)),
            )
    except Exception:  # noqa: BLE001
        logger.exception("写入 entity_sync_status 失败（内存快照仍可用）")


def upsert_entity_sync_checkpoint(
    stream_name: str,
    *,
    watermark_ts: str | None = None,
    watermark_id: str | None = None,
    last_full_at: str | None = None,
    last_ok: bool | None = None,
    last_rows_read: int = 0,
    last_upserted: int = 0,
    last_error: str | None = None,
) -> None:
    """推进单路水位线 / 分表进度（仅 Agent Postgres）。"""
    name = (stream_name or "").strip()
    if not name:
        return
    full_at = last_full_at or _iso_now()
    entry = {
        "stream_name": name,
        "watermark_ts": watermark_ts,
        "watermark_id": watermark_id,
        "last_full_at": full_at,
        "last_ok": last_ok,
        "last_rows_read": int(last_rows_read or 0),
        "last_upserted": int(last_upserted or 0),
        "last_error": last_error,
        "updated_at": _iso_now(),
    }
    _checkpoints[name] = entry
    if _pool is None:
        return
    try:
        with _pool.connection() as conn:
            conn.execute(
                """
                INSERT INTO entity_sync_checkpoint (
                    stream_name, watermark_ts, watermark_id, last_full_at,
                    last_ok, last_rows_read, last_upserted, last_error, updated_at
                ) VALUES (
                    %s,
                    %s::timestamptz,
                    %s,
                    %s::timestamptz,
                    %s,
                    %s,
                    %s,
                    %s,
                    NOW()
                )
                ON CONFLICT (stream_name) DO UPDATE SET
                    watermark_ts = COALESCE(EXCLUDED.watermark_ts, entity_sync_checkpoint.watermark_ts),
                    watermark_id = COALESCE(EXCLUDED.watermark_id, entity_sync_checkpoint.watermark_id),
                    last_full_at = EXCLUDED.last_full_at,
                    last_ok = EXCLUDED.last_ok,
                    last_rows_read = EXCLUDED.last_rows_read,
                    last_upserted = EXCLUDED.last_upserted,
                    last_error = EXCLUDED.last_error,
                    updated_at = NOW()
                """,
                (
                    name,
                    watermark_ts,
                    watermark_id,
                    full_at,
                    last_ok,
                    int(last_rows_read or 0),
                    int(last_upserted or 0),
                    last_error,
                ),
            )
    except Exception:  # noqa: BLE001
        logger.exception("写入 entity_sync_checkpoint 失败 stream=%s", name)


def list_entity_sync_checkpoints() -> list[dict[str, Any]]:
    """返回当前水位线快照（按 stream_name 排序）。"""
    return [dict(_checkpoints[k]) for k in sorted(_checkpoints)]


def get_entity_sync_snapshot() -> dict[str, Any]:
    """运营可观测快照：最近一次结果 + 水位线 + 持久化模式。"""
    from app.sync.entity_sync_service import is_entity_sync_running

    return {
        "in_progress": is_entity_sync_running(),
        "at": _last_at,
        "result": dict(_last_result) if _last_result is not None else None,
        "persisted": _pool is not None,
        "checkpoints": list_entity_sync_checkpoints(),
    }


def clear_entity_sync_persistence(*, clear_db: bool = False) -> None:
    """测试用：清空内存；可选清空 Postgres。"""
    global _last_at, _last_result, _checkpoints
    _last_at = None
    _last_result = None
    _checkpoints.clear()
    if not clear_db or _pool is None:
        return
    with _pool.connection() as conn:
        conn.execute("DELETE FROM entity_sync_status")
        conn.execute("DELETE FROM entity_sync_checkpoint")
