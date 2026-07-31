"""父图 astream_events(v3) → SSE 事件流（零兼容：无图外 pending HITL）。"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any, cast

from langgraph.types import Command

from app.graph.parent_graph import ParentState
from app.utils.runnable_config import thread_runnable_config

logger = logging.getLogger(__name__)


async def stream_parent_graph(
    *,
    thread_id: str,
    model_id: str,
    input_payload: ParentState | Command[Any] | dict[str, Any],
    auth_token: str | None = None,
) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    """
    对父 StateGraph 执行 ``astream_events(version="v3")`` 并映射为 SSE 元组。

    支持初始 state dict 与 ``Command(resume=...)`` 续跑。
    """
    from platform_mcp.runtime.agent_debug import agent_debug
    from platform_mcp.runtime.context import (
        current_auth_token,
        current_model_id,
        current_stream_message_skip,
        current_thread_id,
        safe_reset_contextvar,
    )

    from app.graph.agent_stream_adapter import iter_agent_sse_events_async
    from app.graph.checkpoint_utils import checkpoint_message_count
    from app.graph.parent_graph import build_parent_graph

    config = thread_runnable_config(thread_id)
    graph = build_parent_graph(model_id=model_id)
    skip_count = await checkpoint_message_count(thread_id, model_id)
    skip_token = current_stream_message_skip.set(skip_count)
    auth_token_reset = current_auth_token.set(auth_token)
    tid_reset = current_thread_id.set(thread_id)
    mid_reset = current_model_id.set(model_id)

    agent_debug(
        "flow.parent.stream_start",
        thread_id=thread_id,
        model_id=model_id,
        input_kind=type(input_payload).__name__,
        skip_count=skip_count,
    )

    # 官方：初始 state 或 Command(resume=...)；dict 与 ParentState 结构兼容，运行时安全
    stream_input = cast(ParentState | Command[Any] | None, input_payload)

    try:
        from langgraph.stream.transformers import CustomTransformer

        # 官方：plan_execute / bpmn_execute 经 get_stream_writer 发 custom；
        # v3 默认 mux 无 CustomTransformer，须显式追加才能投影到 stream.custom
        async for event_name, event_payload in iter_agent_sse_events_async(
            graph.astream_events(
                stream_input,
                config=config,
                version="v3",
                transformers=[CustomTransformer],
            ),
            model_id=model_id,
        ):
            if event_name == "__custom__":
                custom = event_payload if isinstance(event_payload, dict) else {}
                sse = custom.get("sse_event")
                body = {k: v for k, v in custom.items() if k != "sse_event"}
                if sse == "tool_start":
                    start_payload: dict[str, Any] = {
                        "tool": body.get("tool"),
                        "args": body.get("args") or {},
                    }
                    if body.get("retry"):
                        start_payload["retry"] = True
                        start_payload["attempt"] = body.get("attempt")
                    yield ("tool_start", start_payload)
                elif sse == "tool_end":
                    end_payload: dict[str, Any] = {
                        "tool": body.get("tool"),
                        "result": body.get("result") or "",
                    }
                    if body.get("retry"):
                        end_payload["retry"] = True
                        end_payload["attempt"] = body.get("attempt")
                    yield ("tool_end", end_payload)
                elif sse == "replan":
                    yield ("replan", body)
                elif sse == "message":
                    yield ("message", body)
                elif sse == "plan_update":
                    yield ("plan_update", body)
                elif sse == "interrupt":
                    yield ("interrupt", body)
                elif sse == "error":
                    yield ("error", body)
                continue
            yield (event_name, event_payload)
    except Exception as exc:
        from app.services.llm_error_mapper import format_llm_error_event

        logger.exception("父图流式执行失败: thread=%s", thread_id)
        yield (
            "error",
            format_llm_error_event(exc, code=50002, fallback_message="Agent 执行失败"),
        )
    finally:
        safe_reset_contextvar(
            current_stream_message_skip, skip_token, label="current_stream_message_skip"
        )
        safe_reset_contextvar(current_auth_token, auth_token_reset, label="current_auth_token")
        safe_reset_contextvar(current_thread_id, tid_reset, label="current_thread_id")
        safe_reset_contextvar(current_model_id, mid_reset, label="current_model_id")
