"""新消息对话应用用例。"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.messages import HumanMessage

from app.graph.context import assemble_context
from contracts.context import (
    current_auth_token,
    current_message_id,
    current_thread_id,
    current_turn_suppressed_tools,
    safe_reset_contextvar,
)

AgentEvent = tuple[str, dict[str, Any]]


async def stream_chat_core(
    *,
    thread_id: str,
    model_id: str,
    message: str,
    metadata: dict[str, Any] | None = None,
    auth_token: str | None = None,
    recent_user_messages: list[str] | None = None,
    mid: str | None = None,
) -> AsyncIterator[AgentEvent]:
    """执行新消息：组装上下文、清理 stale 状态、驱动父 StateGraph。"""
    from app.models.router import require_model_credentials

    require_model_credentials()
    token = current_auth_token.set(auth_token)
    tid = current_thread_id.set(thread_id)
    turn_mid = (mid or "").strip() or str(uuid.uuid4())
    mid_token = current_message_id.set(turn_mid)

    from app.services.prompt_assembly import resolve_recent_messages_for_intent

    _, intent_note = resolve_recent_messages_for_intent(message, recent_user_messages)
    suppressed_token = None
    if intent_note:
        suppressed_token = current_turn_suppressed_tools.set(frozenset({"download_file"}))
    try:
        ctx = assemble_context(
            thread_id=thread_id,
            message=message,
            metadata=metadata,
            recent_user_messages=recent_user_messages,
        )

        from app.services.session_store import clear_thread_orchestration
        from contracts.agent_debug import agent_debug, orchestration_snapshot

        before = orchestration_snapshot(thread_id)
        clear_thread_orchestration(thread_id)
        agent_debug(
            "chat.orchestration_clear",
            thread_id=thread_id,
            message_preview=(message or "")[:80],
            before=before,
            after=orchestration_snapshot(thread_id),
        )

        from app.graph.checkpoint_utils import (
            abandon_stale_checkpoint_interrupt,
            checkpoint_messages_summary,
            parent_has_pending_interrupt,
            repair_dangling_tool_calls,
        )

        if await parent_has_pending_interrupt(thread_id, model_id):
            agent_debug(
                "chat.abandon_stale_interrupt",
                thread_id=thread_id,
                message_preview=(message or "")[:80],
            )
            await abandon_stale_checkpoint_interrupt(thread_id, model_id)

        repaired = await repair_dangling_tool_calls(thread_id, model_id)
        if repaired:
            agent_debug(
                "chat.repair_dangling_tool_calls",
                thread_id=thread_id,
                repaired_count=repaired,
            )

        agent_debug(
            "flow.checkpoint.before_chat",
            thread_id=thread_id,
            mid=turn_mid,
            checkpoint_messages=await checkpoint_messages_summary(thread_id, model_id),
        )

        initial_state = {
            "messages": [
                HumanMessage(
                    content=ctx.llm_user_message,
                    id=turn_mid,
                    additional_kwargs={"mid": turn_mid},
                )
            ],
            "user_message": ctx.message,
            "llm_user_message": ctx.llm_user_message,
            "model_id": model_id,
            "metadata": {**(dict(ctx.metadata or {})), "mid": turn_mid},
        }

        from app.graph.parent_graph_stream import stream_parent_graph

        saw_terminal = False
        saw_interrupt = False
        async for event in stream_parent_graph(
            thread_id=thread_id,
            model_id=model_id,
            input_payload=initial_state,
            auth_token=auth_token,
        ):
            if event[0] in ("done", "error"):
                saw_terminal = True
            if event[0] == "interrupt":
                saw_interrupt = True
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

        if not saw_interrupt:
            from app.graph.checkpoint_utils import (
                collect_pending_interrupt_payloads,
                enrich_interrupt_payload_mid,
            )

            turn_mid = (current_message_id.get() or "").strip() or None
            for payload in await collect_pending_interrupt_payloads(thread_id, model_id):
                enriched = enrich_interrupt_payload_mid(payload, fallback_mid=turn_mid)
                agent_debug(
                    "chat.hitl_interrupt_recovery",
                    thread_id=thread_id,
                    interrupt_type=enriched.get("type"),
                    tool=enriched.get("tool"),
                    mid=enriched.get("mid"),
                )
                if enriched.get("type") == "plan_confirm":
                    from app.services.plan_graph import build_plan_sse_payload

                    steps = enriched.get("steps") or []
                    yield (
                        "plan",
                        build_plan_sse_payload(
                            steps if isinstance(steps, list) else [],
                            graph=enriched.get("graph"),
                        ),
                    )
                yield ("interrupt", enriched)

        if not saw_terminal:
            yield ("done", {"type": "done", "thread_id": thread_id})
    finally:
        if suppressed_token is not None:
            safe_reset_contextvar(
                current_turn_suppressed_tools,
                suppressed_token,
                label="current_turn_suppressed_tools",
            )
        safe_reset_contextvar(current_auth_token, token, label="current_auth_token")
        safe_reset_contextvar(current_thread_id, tid, label="current_thread_id")
        safe_reset_contextvar(current_message_id, mid_token, label="current_message_id")


async def stream_chat(
    *,
    thread_id: str,
    model_id: str,
    message: str,
    metadata: dict[str, Any] | None = None,
    auth_token: str | None = None,
    recent_user_messages: list[str] | None = None,
    user_id: str | None = None,
    mid: str | None = None,
) -> AsyncIterator[AgentEvent]:
    """执行新用户消息，并包装 Plan、Trace 与审计事件。"""
    from app.graph.stream_envelope import wrap_stream_with_plan_trace
    from app.middleware.auth import get_current_user_id

    if not user_id:
        user_id = await get_current_user_id(auth_token)

    async for event in wrap_stream_with_plan_trace(
        stream_chat_core(
            thread_id=thread_id,
            model_id=model_id,
            message=message,
            metadata=metadata,
            auth_token=auth_token,
            recent_user_messages=recent_user_messages,
            mid=mid,
        ),
        thread_id=thread_id,
        run_id=str(uuid.uuid4()),
        user_id=user_id,
        user_message=message,
        plan_steps=None,
        auto_replan=False,
    ):
        yield event
