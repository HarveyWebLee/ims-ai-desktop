"""BPMN 图 Plan 执行：工具调用、HITL 暂存与 resume 续跑。"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from app.application.execution.bpmn_executor import execute_bpmn_graph
from app.application.execution.bpmn_graph import ExecutionGraph, build_execution_graph
from app.application.execution.execution_context import ExecutionContext
from app.application.execution.plan_runner import execute_planned_step
from app.services.bpmn_execution_state import (
    clear_bpmn_execution_state,
)


def _resolve_paused_node_id(ctx: ExecutionContext) -> str | None:
    """查找当前 awaiting_hitl 的节点 id。"""
    for node_id, runtime in ctx.node_runtimes.items():
        if runtime.status == "awaiting_hitl":
            return node_id
    return None


def resolve_bpmn_resume_start_node(
    graph: ExecutionGraph,
    ctx: ExecutionContext,
    paused_node_id: str | None,
) -> str:
    """HITL 工具完成后，从暂停节点的后继继续遍历。"""
    from app.application.execution.bpmn_executor import _resolve_next_node_id

    if paused_node_id and paused_node_id in graph.nodes:
        next_id = _resolve_next_node_id(graph, ctx, paused_node_id)
        if next_id:
            return next_id
    return graph.start_id


async def execute_bpmn_plan(
    flow_document: dict[str, Any],
    params_by_tool: dict[str, dict[str, Any]],
    user_message: str,
    *,
    thread_id: str = "",
    auth_token: str | None = None,
    model_id: str = "",
    resume_ctx: ExecutionContext | None = None,
    resume_start_node_id: str | None = None,
) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    """
    生产环境 BPMN 图执行入口。

    - 工具经 execute_planned_step / preflight / HITL 完整链路
    - interrupt 时由父图节点 ``interrupt()`` 暂停（不写 pending_tool_hitl）
    - 正常结束清除 execution_state
    """

    from contracts.context import current_thread_id

    effective_thread_id = (thread_id or current_thread_id.get() or "").strip()
    graph = build_execution_graph(flow_document)
    ctx = resume_ctx or ExecutionContext(
        thread_id=effective_thread_id,
        user_message=user_message,
        globals={"user_message": user_message},
    )
    start_from = resume_start_node_id or graph.start_id
    tool_params = dict(params_by_tool or {})

    async def _stream_step(node: Any, params: dict[str, Any], msg: str):
        step = {
            "id": node.id,
            "label": str(node.data.get("title") or node.id),
            "tool": node.data.get("tool"),
            "status": "running",
        }
        from app.services.plan_confirm import resolve_step_tool_params

        resolved = resolve_step_tool_params(step, tool_params, msg)
        async for event in execute_planned_step(
            step,
            resolved,
            auth_token=auth_token,
            thread_id=effective_thread_id or None,
        ):
            yield event

    saw_done = False
    async for event in execute_bpmn_graph(
        flow_document,
        ctx=ctx,
        graph=graph,
        params_by_tool=tool_params,
        user_message=user_message,
        start_from_node_id=start_from,
        stream_step=_stream_step,
    ):
        if event[0] == "plan_update" and isinstance(event[1], dict):
            from app.services.bpmn_observability import record_bpmn_execute

            payload = event[1]
            node_id = str(payload.get("node_id") or payload.get("step_id") or "")
            status = str(payload.get("status") or "")
            if node_id and status:
                record_bpmn_execute(
                    node_id=node_id,
                    status=status,
                    branch=str(payload.get("matchedBranchKey") or "") or None,
                    tool=str(payload.get("tool") or "") or None,
                    thread_id=effective_thread_id or None,
                )

        if event[0] == "interrupt":
            from app.services.bpmn_execution_state import set_bpmn_execution_state
            from app.services.bpmn_observability import record_hitl_lifecycle
            from contracts.agent_debug import agent_debug

            payload = event[1] if isinstance(event[1], dict) else {}
            paused_node_id = _resolve_paused_node_id(ctx)
            tool_name = str(payload.get("tool") or "")
            tool_args: dict[str, Any] = {}
            if isinstance(payload.get("args"), dict):
                tool_args = dict(payload["args"])
            elif tool_name and isinstance(tool_params.get(tool_name), dict):
                tool_args = dict(tool_params[tool_name])
            agent_debug(
                "execute.bpmn_graph_hitl_pause",
                thread_id=effective_thread_id,
                tool=tool_name,
                paused_node_id=paused_node_id or "",
            )
            record_hitl_lifecycle(
                action="emit",
                interrupt_type=str(payload.get("type") or "confirm"),
                tool=tool_name or None,
                thread_id=effective_thread_id or None,
            )
            # 节点重启后续跑依赖本暂存（AC-30：不重跑已完成节点）
            if effective_thread_id:
                set_bpmn_execution_state(
                    effective_thread_id,
                    {
                        "paused_node_id": paused_node_id,
                        "ctx": ctx.to_state_dict(),
                        "interrupt_payload": payload,
                        "tool": tool_name,
                        "tool_args": tool_args,
                    },
                )
            yield event
            return

        if event[0] == "done":
            saw_done = True

        yield event

    if saw_done and effective_thread_id:
        clear_bpmn_execution_state(effective_thread_id)
