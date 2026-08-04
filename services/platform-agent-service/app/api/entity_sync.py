"""
实体表 → 向量库同步 API。

POST /api/agent/entity-sync
"""

from __future__ import annotations

import asyncio
from typing import Any

from pydantic import BaseModel, Field

from app.api.response import fail, ok
from app.infrastructure.db.dameng_readonly import DamengReadOnlyError
from app.middleware.auth import get_current_user_id
from app.sync.entity_sync_service import run_entity_sync
from app.sync.entity_sync_status import get_entity_sync_status, remember_entity_sync_result


class EntitySyncRequest(BaseModel):
    """可选覆盖 ENTITY_SYNC_TABLES；默认用服务端配置。"""

    tables: str | None = Field(
        default=None,
        description="覆盖表配置：空跳过；*=全部；逗号分隔表名",
    )


async def entity_sync_status(authorization: str | None = None) -> dict[str, Any]:
    """最近一次同步结果 + 是否进行中。"""
    await get_current_user_id(authorization)
    return ok(get_entity_sync_status())


async def trigger_entity_sync(
    body: EntitySyncRequest | None = None,
    authorization: str | None = None,
) -> dict[str, Any]:
    """鉴权后在线程池执行同步，避免阻塞事件循环。"""
    await get_current_user_id(authorization)
    override = body.tables if body is not None else None

    try:
        result = await asyncio.to_thread(run_entity_sync, tables_override=override)
    except DamengReadOnlyError as exc:
        payload = fail(40052, str(exc), {"reason": "dm_connect_error"})
        remember_entity_sync_result(
            {"ok": False, "skipped": True, "reason": "dm_connect_error", "message": str(exc)}
        )
        return payload
    except Exception as exc:  # noqa: BLE001
        payload = fail(50052, f"同步执行异常: {exc}", {"reason": "unexpected_error"})
        remember_entity_sync_result(
            {
                "ok": False,
                "skipped": False,
                "reason": "unexpected_error",
                "message": f"同步执行异常: {exc}",
            }
        )
        return payload

    remember_entity_sync_result(result)

    if result.get("skipped") and result.get("reason") == "sync_in_progress":
        return fail(40901, str(result.get("message") or "同步进行中"), result)
    if result.get("skipped") and result.get("reason") == "empty_config":
        return ok(result, message=str(result.get("message") or "ok"))
    if not result.get("ok") and result.get("skipped"):
        return fail(40051, str(result.get("message") or "同步未执行"), result)
    if not result.get("ok"):
        return fail(50051, str(result.get("message") or "同步失败"), result)
    return ok(result, message=str(result.get("message") or "ok"))
