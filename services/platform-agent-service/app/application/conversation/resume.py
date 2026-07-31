"""HITL 续跑应用用例：一律 ``Command(resume=...)`` 驱动父 StateGraph。"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Any

from langgraph.types import Command
from platform_mcp.runtime.context import (
    current_auth_token,
    current_hitl_confirm_bypass,
    current_thread_id,
    current_turn_suppressed_tools,
    safe_reset_contextvar,
)

AgentEvent = tuple[str, dict[str, Any]]


def _unwrap_resume_args(resume_value: Any) -> Any:
    if isinstance(resume_value, dict) and "args" in resume_value:
        return resume_value["args"]
    return resume_value


def _normalize_resume_payload(resume_value: Any) -> Any:
    from platform_mcp.runtime.hitl import strip_hitl_meta_from_resume

    return strip_hitl_meta_from_resume(_unwrap_resume_args(resume_value))


async def stream_resume_core(
    *,
    thread_id: str,
    model_id: str,
    resume_value: Any,
    auth_token: str | None = None,
    user_id: str | None = None,
) -> AsyncIterator[AgentEvent]:
    """执行 HITL 续跑：仅 ``Command(resume=...)`` 路径。"""
    from app.graph.stream_envelope import wrap_stream_with_plan_trace
    from app.middleware.auth import get_current_user_id
    from app.models.router import require_model_credentials

    require_model_credentials()

    if not user_id:
        user_id = await get_current_user_id(auth_token)

    from platform_mcp.runtime.hitl import (
        extract_expected_hitl_tool,
        is_hitl_approve,
        is_hitl_reject,
    )

    run_id = str(uuid.uuid4())
    token = current_auth_token.set(auth_token)
    tid = current_thread_id.set(thread_id)
    from platform_mcp.runtime.agent_debug import agent_debug

    agent_debug("resume.context.init", thread_id=thread_id, has_auth=bool(auth_token))
    expected_resume_tool = extract_expected_hitl_tool(resume_value)
    suppressed_token = None
    if expected_resume_tool and expected_resume_tool != "download_file":
        suppressed_token = current_turn_suppressed_tools.set(frozenset({"download_file"}))

    bypass_token = None
    resume_payload = _normalize_resume_payload(resume_value)
    if is_hitl_approve(resume_payload):
        from app.graph.checkpoint_utils import parent_has_pending_interrupt

        if await parent_has_pending_interrupt(thread_id, model_id):
            bypass_token = current_hitl_confirm_bypass.set(True)

    from app.services.session_store import session_store

    prior_msgs = session_store.get_user_messages(thread_id, limit=1)
    resume_user_msg = prior_msgs[-1] if prior_msgs else "继续执行"

    plan_for_wrap = None
    plan_graph_for_wrap = None
    plan_flow_doc_for_wrap = None
    if isinstance(resume_payload, dict) and resume_payload.get("type") == "approve":
        bpmn_snap = session_store.get_thread_bpmn_snapshot(thread_id)
        if isinstance(bpmn_snap, dict):
            steps = bpmn_snap.get("steps")
            if isinstance(steps, list):
                plan_for_wrap = steps
            if isinstance(bpmn_snap.get("graph"), dict):
                plan_graph_for_wrap = bpmn_snap["graph"]
            if isinstance(bpmn_snap.get("flow_document"), dict):
                plan_flow_doc_for_wrap = bpmn_snap["flow_document"]

    async def _resume_inner() -> AsyncIterator[AgentEvent]:
        from app.graph.checkpoint_utils import checkpoint_messages_summary

        agent_debug(
            "resume.start",
            thread_id=thread_id,
            resume_type=(resume_payload.get("type") if isinstance(resume_payload, dict) else None),
        )
        agent_debug(
            "flow.checkpoint.before_resume",
            thread_id=thread_id,
            checkpoint_messages=await checkpoint_messages_summary(thread_id, model_id),
        )

        if is_hitl_reject(resume_payload):
            from app.graph.checkpoint_utils import (
                abandon_stale_checkpoint_interrupt,
                parent_has_pending_interrupt,
            )
            from app.services.session_store import clear_thread_bpmn_snapshot

            has_ckpt = await parent_has_pending_interrupt(thread_id, model_id)
            agent_debug("resume.reject", thread_id=thread_id, checkpoint_interrupt=has_ckpt)
            if has_ckpt:
                await abandon_stale_checkpoint_interrupt(thread_id, model_id)
            clear_thread_bpmn_snapshot(thread_id)
            yield (
                "message",
                {"type": "text", "delta": "已取消操作。如需调整，请重新描述您的需求。"},
            )
            yield ("done", {"type": "done", "thread_id": thread_id})
            return

        from app.graph.parent_graph_stream import stream_parent_graph

        saw_terminal = False
        async for event in stream_parent_graph(
            thread_id=thread_id,
            model_id=model_id,
            input_payload=Command(resume=resume_payload),
            auth_token=auth_token,
        ):
            if event[0] in ("done", "error"):
                saw_terminal = True
            if event[0] == "interrupt":
                payload = event[1] if isinstance(event[1], dict) else {}
                if payload.get("type") == "plan_confirm":
                    from app.services.plan_graph import build_plan_sse_payload

                    steps = payload.get("steps") or []
                    yield (
                        "plan",
                        build_plan_sse_payload(
                            steps if isinstance(steps, list) else [],
                            graph=payload.get("graph"),
                        ),
                    )
            yield event

        if not saw_terminal:
            yield ("done", {"type": "done", "thread_id": thread_id})

    try:
        async for event in wrap_stream_with_plan_trace(
            _resume_inner(),
            thread_id=thread_id,
            run_id=run_id,
            user_id=user_id,
            user_message=resume_user_msg,
            plan_steps=plan_for_wrap,
            plan_graph=plan_graph_for_wrap,
            plan_flow_document=plan_flow_doc_for_wrap,
            auto_replan=False,
        ):
            yield event
    finally:
        if suppressed_token is not None:
            safe_reset_contextvar(
                current_turn_suppressed_tools,
                suppressed_token,
                label="current_turn_suppressed_tools",
            )
        safe_reset_contextvar(current_auth_token, token, label="current_auth_token")
        safe_reset_contextvar(current_thread_id, tid, label="current_thread_id")
        if bypass_token is not None:
            safe_reset_contextvar(
                current_hitl_confirm_bypass,
                bypass_token,
                label="current_hitl_confirm_bypass",
            )


async def stream_resume(
    *,
    thread_id: str,
    model_id: str,
    resume_value: Any,
    auth_token: str | None = None,
    user_id: str | None = None,
) -> AsyncIterator[AgentEvent]:
    """执行完整 HITL 续跑事件流。"""
    async for event in stream_resume_core(
        thread_id=thread_id,
        model_id=model_id,
        resume_value=resume_value,
        auth_token=auth_token,
        user_id=user_id,
    ):
        yield event
