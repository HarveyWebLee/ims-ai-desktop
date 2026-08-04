"""client_action 执行回执 API（P2-2）。

桌面/宿主执行完 navigate / openModal 等后上报；写入 audit，不进入图、不替代 HITL。
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.api.response import fail, ok
from app.api.thread_access import can_read_thread
from app.middleware.auth import get_current_user_id
from app.persistence.bootstrap import is_postgres_enabled
from app.services.audit_store import audit_store, mask_payload_summary


class ClientActionResultBody(BaseModel):
    """与 @ims/shared-types ClientActionResult 对齐。"""

    action: Literal[
        "navigate",
        "openModal",
        "download",
        "toast",
        "refresh",
        "pause",
    ]
    ok: bool
    skipped: bool = False
    summary: str | None = None
    error: str | None = None
    path: str | None = None
    modal: str | None = None
    run_id: str | None = Field(default=None, description="可选关联本轮 run")


async def report_client_action_result(
    thread_id: str,
    body: ClientActionResultBody,
    authorization: str | None = None,
) -> dict[str, Any]:
    """鉴权 + 会话归属校验后写入 client_action_result 审计。"""
    user_id = await get_current_user_id(authorization)
    tid = (thread_id or "").strip()
    if not tid:
        return fail(40071, "thread_id 不能为空")

    if is_postgres_enabled() and not can_read_thread(user_id, tid):
        return fail(40471, "会话不存在或无权访问")

    summary = mask_payload_summary(
        {
            "action": body.action,
            "ok": body.ok,
            "skipped": body.skipped,
            "summary": (body.summary or "")[:200] or None,
            "error": (body.error or "")[:200] or None,
            "path": body.path,
            "modal": body.modal,
        }
    )
    try:
        audit_store.append(
            thread_id=tid,
            user_id=user_id,
            event_type="client_action_result",
            run_id=body.run_id,
            tool_name=body.action,
            payload_summary=summary,
        )
    except Exception as exc:  # noqa: BLE001
        return fail(50071, f"回执写入失败: {exc}")

    return ok(
        {
            "thread_id": tid,
            "action": body.action,
            "ok": body.ok,
            "skipped": body.skipped,
        },
        message="ok",
    )
