"""AUTO / MANUAL 任务节点处理器。"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Callable
from typing import Any

from app.application.execution.bpmn_graph import ExecutionGraph, ExecutionNode
from app.application.execution.execution_context import ExecutionContext
from app.services.task_planner import parse_tool_result

StepRunner = Callable[
    [ExecutionNode, dict[str, Any], str],
    AsyncIterator[tuple[str, dict[str, Any]]],
]


async def run_auto_node(
    node: ExecutionNode,
    ctx: ExecutionContext,
    graph: ExecutionGraph,
    *,
    params: dict[str, Any] | None = None,
    user_message: str = "",
    stream_step: StepRunner | None = None,
) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    """执行绑定工具的 AUTO/MANUAL 节点。"""
    _ = graph
    tool_name = str(node.data.get("tool") or "").strip()
    if not tool_name:
        ctx.mark_node(node.id, node.type, "error")
        yield (
            "error",
            {"message": f"节点「{node.data.get('title') or node.id}」未绑定工具"},
        )
        return

    ctx.mark_node(node.id, node.type, "running")
    yield (
        "plan_update",
        {
            "step_id": node.id,
            "node_id": node.id,
            "node_type": node.type,
            "status": "running",
            "tool": tool_name,
        },
    )

    tool_args = dict(params or {})
    last_result = ""

    if stream_step is not None:
        async for event in stream_step(node, tool_args, user_message):
            if event[0] == "interrupt":
                ctx.mark_node(node.id, node.type, "awaiting_hitl")
                yield (
                    "plan_update",
                    {
                        "step_id": node.id,
                        "node_id": node.id,
                        "node_type": node.type,
                        "status": "awaiting_hitl",
                        "tool": tool_name,
                    },
                )
                yield event
                return
            if event[0] == "tool_end" and event[1].get("tool") == tool_name:
                last_result = str(event[1].get("result") or "")
            yield event
    else:
        result = json.dumps({"ok": True, "summary": "mock"}, ensure_ascii=False)
        last_result = result
        yield ("tool_start", {"tool": tool_name, "args": tool_args})
        yield ("tool_end", {"tool": tool_name, "result": result})

    ok, summary, _stop_retry, user_cancelled = parse_tool_result(last_result)
    if user_cancelled:
        ctx.mark_node(node.id, node.type, "skipped", skip_reason=summary or "用户取消")
        yield (
            "plan_update",
            {
                "step_id": node.id,
                "node_id": node.id,
                "node_type": node.type,
                "status": "skipped",
                "tool": tool_name,
                "skipReason": summary,
            },
        )
        return
    if not ok:
        # 含 authentication_required 等 stop_retry 硬失败：标 error，禁止当 skipped
        ctx.mark_node(node.id, node.type, "error")
        yield (
            "plan_update",
            {
                "step_id": node.id,
                "node_id": node.id,
                "node_type": node.type,
                "status": "error",
                "tool": tool_name,
                "skipReason": summary,
            },
        )
        return

    ctx.set_node_output(node.id, last_result)
    ctx.mark_node(node.id, node.type, "done")
    yield (
        "plan_update",
        {
            "step_id": node.id,
            "node_id": node.id,
            "node_type": node.type,
            "status": "done",
            "tool": tool_name,
        },
    )
