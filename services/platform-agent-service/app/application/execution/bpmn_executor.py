"""BPMN 图遍历执行器（P1：线性链 + 排他条件网关）。"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from typing import Any

from app.application.execution.bpmn_graph import ExecutionGraph, build_execution_graph
from app.application.execution.execution_context import ExecutionContext
from app.application.execution.node_handlers.auto import run_auto_node
from app.application.execution.node_handlers.condition import run_condition_node
from app.application.execution.node_handlers.start_end import run_end_node, run_start_node

_TASK_TYPES = frozenset({"AUTO", "MANUAL", "LLM"})
_GATEWAY_TYPES = frozenset({"CONDITION"})
_START_TYPES = frozenset({"start", "START"})
_END_TYPES = frozenset({"end", "END"})

StepRunner = Callable[
    [Any, dict[str, Any], str],
    AsyncIterator[tuple[str, dict[str, Any]]],
]


def _resolve_next_node_id(
    graph: ExecutionGraph,
    ctx: ExecutionContext,
    current_id: str,
) -> str | None:
    """根据当前节点类型与上下文解析下一节点。"""
    node = graph.nodes.get(current_id)
    if node is None:
        return None
    if node.type in _END_TYPES:
        return None
    if node.type in _GATEWAY_TYPES:
        runtime = ctx.node_runtimes.get(current_id)
        port = runtime.matched_branch_key if runtime else None
        if not port:
            return None
        return graph.successor_by_port(current_id, port)
    return graph.unique_successor(current_id)


async def execute_bpmn_graph(
    flow_document: dict[str, Any],
    *,
    ctx: ExecutionContext | None = None,
    params_by_tool: dict[str, dict[str, Any]] | None = None,
    user_message: str = "",
    start_from_node_id: str | None = None,
    stream_step: StepRunner | None = None,
    graph: ExecutionGraph | None = None,
) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    """
    按 BPMN 图遍历执行。

    参数:
        flow_document: 画布 JSON
        ctx: 执行上下文；缺省则新建
        params_by_tool: 工具参数表（与 plan_runner 一致）
        start_from_node_id: resume 起点（迭代 2）
        stream_step: 注入工具执行流（测试与生产共用）
    """
    execution_graph = graph or build_execution_graph(flow_document)
    execution_ctx = ctx or ExecutionContext(
        user_message=user_message,
        globals={"user_message": user_message},
    )
    tool_params = dict(params_by_tool or {})

    cursor = start_from_node_id or execution_graph.start_id
    if cursor not in execution_graph.nodes:
        yield ("error", {"message": f"起始节点不存在: {cursor}"})
        return

    interrupted = False

    while cursor:
        node = execution_graph.nodes.get(cursor)
        if node is None:
            break

        runtime = execution_ctx.node_runtimes.get(cursor)
        if runtime and runtime.status == "skipped":
            cursor = _resolve_next_node_id(execution_graph, execution_ctx, cursor)
            continue

        if node.type in _START_TYPES:
            async for event in run_start_node(node, execution_ctx, execution_graph):
                yield event
        elif node.type in _END_TYPES:
            async for event in run_end_node(node, execution_ctx, execution_graph):
                yield event
            break
        elif node.type in _GATEWAY_TYPES:
            async for event in run_condition_node(node, execution_ctx, execution_graph):
                if event[0] == "error":
                    return
                yield event
        elif node.type in _TASK_TYPES:
            tool_name = str(node.data.get("tool") or "")
            params = dict(tool_params.get(tool_name) or {})
            async for event in run_auto_node(
                node,
                execution_ctx,
                execution_graph,
                params=params,
                user_message=user_message,
                stream_step=stream_step,
            ):
                if event[0] == "interrupt":
                    interrupted = True
                if event[0] == "error":
                    return
                yield event
            if interrupted:
                return
            runtime_after = execution_ctx.node_runtimes.get(cursor)
            if runtime_after and runtime_after.status == "error":
                return
            if runtime_after and runtime_after.status == "skipped":
                return
        else:
            execution_ctx.mark_node(cursor, node.type, "skipped", skip_reason="不支持的节点类型")
            yield (
                "plan_update",
                {
                    "step_id": cursor,
                    "node_id": cursor,
                    "node_type": node.type,
                    "status": "skipped",
                    "skipReason": "不支持的节点类型",
                },
            )

        if node.type in _END_TYPES:
            break

        next_id = _resolve_next_node_id(execution_graph, execution_ctx, cursor)
        if not next_id:
            break
        cursor = next_id

    yield ("done", {"type": "done", "mode": "bpmn_graph"})
