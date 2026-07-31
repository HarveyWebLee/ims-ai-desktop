"""
BPMN / HITL 运维可观测：结构化日志 + audit_store。

事件类型（非 SSE，直接 append）：
- bpmn_compile：LLM 条件编译成败与回退
- bpmn_execute：图节点步进状态
- hitl_lifecycle：interrupt 下发与 approve/reject/abort
"""

from __future__ import annotations

import logging
import time
from typing import Any, Literal

logger = logging.getLogger(__name__)

FallbackKind = Literal["none", "d1", "react", "disabled"]
HitlAction = Literal["emit", "approve", "reject", "abort"]


def _resolve_thread_id(thread_id: str | None) -> str:
    tid = (thread_id or "").strip()
    if tid:
        return tid
    try:
        from platform_mcp.runtime.context import current_thread_id

        return str(current_thread_id.get() or "").strip()
    except Exception:
        return ""


def _resolve_user_id(user_id: str | None) -> str:
    uid = (user_id or "").strip()
    if uid:
        return uid
    try:
        from platform_mcp.runtime.context import current_auth_token

        from app.middleware.auth import resolve_user_id_from_token

        token = current_auth_token.get()
        if token:
            return resolve_user_id_from_token(token)
    except Exception:
        pass
    return "system"


def record_audit_event(
    event_type: str,
    *,
    thread_id: str | None = None,
    user_id: str | None = None,
    tool_name: str | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    """写入 audit（失败不抛）；并打结构化日志。"""
    tid = _resolve_thread_id(thread_id)
    summary = dict(payload or {})
    if tid and "thread_id" not in summary:
        summary["thread_id"] = tid

    logger.info(
        "bpmn_obs event=%s tool=%s payload=%s",
        event_type,
        tool_name or "",
        summary,
    )

    if not tid:
        return
    try:
        from app.services.audit_store import audit_store, mask_payload_summary

        audit_store.append(
            thread_id=tid,
            user_id=_resolve_user_id(user_id),
            event_type=event_type,
            tool_name=tool_name,
            payload_summary=mask_payload_summary(summary),
        )
    except Exception:
        logger.debug("bpmn_obs audit append failed", exc_info=True)


def record_bpmn_compile(
    *,
    ok: bool,
    fallback: FallbackKind,
    reason: str,
    duration_ms: int | None = None,
    condition_count: int | None = None,
    thread_id: str | None = None,
    user_id: str | None = None,
) -> None:
    """记录条件 FlowDocument 编译结果。"""
    payload: dict[str, Any] = {
        "ok": ok,
        "fallback": fallback,
        "reason": reason,
    }
    if duration_ms is not None:
        payload["duration_ms"] = duration_ms
    if condition_count is not None:
        payload["condition_count"] = condition_count
    record_audit_event(
        "bpmn_compile",
        thread_id=thread_id,
        user_id=user_id,
        payload=payload,
    )


def record_bpmn_execute(
    *,
    node_id: str,
    status: str,
    branch: str | None = None,
    tool: str | None = None,
    duration_ms: int | None = None,
    thread_id: str | None = None,
    user_id: str | None = None,
) -> None:
    """记录 BPMN 节点步进。"""
    payload: dict[str, Any] = {
        "node_id": node_id,
        "status": status,
    }
    if branch:
        payload["branch"] = branch
    if duration_ms is not None:
        payload["duration_ms"] = duration_ms
    record_audit_event(
        "bpmn_execute",
        thread_id=thread_id,
        user_id=user_id,
        tool_name=tool,
        payload=payload,
    )


def record_hitl_lifecycle(
    *,
    action: HitlAction,
    interrupt_type: str | None = None,
    tool: str | None = None,
    thread_id: str | None = None,
    user_id: str | None = None,
) -> None:
    """记录 HITL 生命周期。"""
    payload: dict[str, Any] = {
        "action": action,
        "interrupt_type": interrupt_type or "",
    }
    record_audit_event(
        "hitl_lifecycle",
        thread_id=thread_id,
        user_id=user_id,
        tool_name=tool,
        payload=payload,
    )


class CompileTimer:
    """编译耗时计时器。"""

    def __init__(self) -> None:
        self._started = time.perf_counter()

    def elapsed_ms(self) -> int:
        return int((time.perf_counter() - self._started) * 1000)


__all__ = [
    "CompileTimer",
    "record_audit_event",
    "record_bpmn_compile",
    "record_bpmn_execute",
    "record_hitl_lifecycle",
]
