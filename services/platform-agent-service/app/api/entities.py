"""
实体术语运营 API（设备/变量等 platform_entities）。

与文档知识库分离：供语音纠错与意图匹配试检索、同步可观测。
"""

from __future__ import annotations

import asyncio
from typing import Any

from pydantic import BaseModel, Field

from app.api.response import fail, ok
from app.config import settings
from app.middleware.auth import get_current_user_id


class EntitySearchBody(BaseModel):
    query: str = Field(..., min_length=1)
    limit: int = Field(default=8, ge=1, le=30)
    entity_types: list[str] | None = Field(
        default=None,
        description="可选过滤：device / variable；空=不限",
    )


class EntityDropBody(BaseModel):
    """清空实体术语 collection；须 confirm=true 作为二次确认。"""

    confirm: bool = Field(default=False, description="必须为 true 才会执行删库")


def _entity_store():
    from app.infrastructure.vector.entity_store import EntityVectorStore

    return EntityVectorStore()


def _hit_to_dict(hit: dict[str, Any]) -> dict[str, Any]:
    payload = dict(hit.get("payload") or {})
    text = str(hit.get("text") or payload.get("text") or "")
    preview = text if len(text) <= 220 else text[:219] + "…"
    return {
        "score": float(hit.get("score") or 0.0),
        "entity_type": str(hit.get("entity_type") or payload.get("entity_type") or ""),
        "entity_key": str(hit.get("entity_key") or payload.get("entity_key") or ""),
        "source": str(hit.get("source") or payload.get("source") or ""),
        "text": text,
        "text_preview": preview,
        # 设备 payload 为 camelCase；兼容旧 snake_case
        "device_code": payload.get("deviceCode") or payload.get("device_code"),
        "device_name": payload.get("deviceName") or payload.get("device_name"),
        "var_name": payload.get("var_name") or payload.get("var_code"),
        "show_name": payload.get("show_name") or payload.get("display_name"),
        "table": payload.get("table")
        or ("p_device" if str(hit.get("entity_type") or "") == "device" else None),
    }


async def entity_stats(authorization: str | None = None) -> dict[str, Any]:
    await get_current_user_id(authorization)
    try:
        from app.infrastructure.vector.client import is_qdrant_configured, probe_qdrant
        from app.sync.entity_sync_service import is_entity_sync_running

        if not is_qdrant_configured():
            return ok(
                {
                    "enabled": False,
                    "ok": False,
                    "collection": settings.qdrant_collection_entities,
                    "points": 0,
                    "sync_tables": settings.entity_sync_tables,
                    "in_progress": False,
                    "message": "未配置 QDRANT_URL",
                }
            )
        probe = await asyncio.to_thread(probe_qdrant)
        store = _entity_store()
        points = await asyncio.to_thread(store.count)
        return ok(
            {
                "enabled": True,
                "ok": bool(probe.get("ok")),
                "collection": settings.qdrant_collection_entities,
                "points": points,
                "sync_tables": settings.entity_sync_tables,
                "in_progress": is_entity_sync_running(),
                "probe": probe,
            }
        )
    except Exception as exc:  # noqa: BLE001
        return fail(50071, f"实体库统计失败: {exc}")


async def entity_search(
    body: EntitySearchBody,
    authorization: str | None = None,
) -> dict[str, Any]:
    await get_current_user_id(authorization)
    try:
        store = _entity_store()
        types = [t.strip() for t in (body.entity_types or []) if t and t.strip()]

        def _run() -> dict[str, Any]:
            hits = store.similarity_search(
                body.query.strip(),
                limit=body.limit,
                entity_types=types or None,
            )
            return {
                "query": body.query.strip(),
                "items": [_hit_to_dict(h) for h in hits],
                "collection": store.collection,
            }

        data = await asyncio.to_thread(_run)
        return ok(data)
    except Exception as exc:  # noqa: BLE001
        return fail(50072, f"实体检索失败: {exc}")


async def entity_drop_collection(
    body: EntityDropBody,
    authorization: str | None = None,
) -> dict[str, Any]:
    """
    删除整个实体术语 collection。

    换 Embedding 模型/维度后须清库再同步；达梦源数据不变，需重新触发实体同步。
    """
    await get_current_user_id(authorization)
    if not body.confirm:
        return fail(40073, "须 confirm=true 二次确认后才能清空实体术语库")
    try:
        from app.infrastructure.vector.client import is_qdrant_configured
        from app.sync.entity_sync_service import is_entity_sync_running

        if not is_qdrant_configured():
            return fail(40074, "未配置 QDRANT_URL，无法清库")
        if is_entity_sync_running():
            return fail(40971, "实体同步进行中，请稍后再清库")
        store = _entity_store()
        collection = store.collection
        dropped = await asyncio.to_thread(store.drop_collection)
        return ok(
            {
                "dropped": dropped,
                "collection": collection,
                "existed": dropped,
            },
            message=(
                f"已清空实体术语库集合 {collection}"
                if dropped
                else f"集合 {collection} 不存在，无需删除"
            ),
        )
    except Exception as exc:  # noqa: BLE001
        return fail(50073, f"清空实体术语库失败: {exc}")
