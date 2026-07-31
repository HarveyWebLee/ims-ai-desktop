"""Plan / BPMN 节点内工具执行（HITL 仅经图内 interrupt）。"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from app.application.execution.common import emit_tool_events
from app.application.tool_execution import (
    enrich_tool_execution_context,
    get_tool_execution_pipeline,
)
from app.domain.tool_execution import ToolExecutionContext, ToolExecutionRequest
from contracts.result import tool_result


async def execute_tool_invoke(
    tool_name: str,
    args: dict[str, Any] | None,
    *,
    retry: bool = False,
    attempt: int = 0,
    auth_token: str | None = None,
    thread_id: str | None = None,
    hitl_confirm_bypass: bool = False,
) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    """执行工具，并按序产出 preflight、tool_start 与 tool_end 事件。"""
    pipeline = get_tool_execution_pipeline()
    prepared = await pipeline.prepare(
        ToolExecutionRequest(
            tool_name=tool_name,
            args=dict(args or {}),
            context=enrich_tool_execution_context(
                ToolExecutionContext(auth_token=auth_token, thread_id=thread_id)
            ),
        )
    )
    if prepared.interrupt:
        yield ("interrupt", prepared.interrupt)
        return
    effective_args = prepared.request.args

    for event in emit_tool_events(
        tool_name,
        effective_args,
        "",
        retry=retry,
        attempt=attempt,
    ):
        if event[0] == "tool_start":
            yield event

    if prepared.denied_result is not None:
        result = prepared.denied_result
    else:
        outcome = await pipeline.invoke(prepared, hitl_confirm_bypass=hitl_confirm_bypass)
        if outcome.interrupt:
            yield ("interrupt", outcome.interrupt)
            return
        result = outcome.result or ""

    if not result:
        result = tool_result(
            ok=False,
            summary="工具未返回执行结果",
            data={"error_code": "empty_tool_result", "tool": tool_name},
        )

    for event in emit_tool_events(
        tool_name,
        effective_args,
        result,
        retry=retry,
        attempt=attempt,
    ):
        if event[0] == "tool_end":
            yield event
