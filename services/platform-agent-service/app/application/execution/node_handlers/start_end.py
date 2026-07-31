"""开始 / 结束节点处理器。"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from app.application.execution.bpmn_graph import ExecutionGraph, ExecutionNode
from app.application.execution.execution_context import ExecutionContext


async def run_start_node(
    node: ExecutionNode,
    ctx: ExecutionContext,
    graph: ExecutionGraph,
) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    _ = graph
    ctx.mark_node(node.id, node.type, "done")
    yield (
        "plan_update",
        {
            "step_id": node.id,
            "node_id": node.id,
            "node_type": node.type,
            "status": "done",
        },
    )


async def run_end_node(
    node: ExecutionNode,
    ctx: ExecutionContext,
    graph: ExecutionGraph,
) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    _ = graph
    ctx.mark_node(node.id, node.type, "done")
    yield (
        "plan_update",
        {
            "step_id": node.id,
            "node_id": node.id,
            "node_type": node.type,
            "status": "done",
        },
    )
