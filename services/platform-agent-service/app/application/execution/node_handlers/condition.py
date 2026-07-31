"""CONDITION 排他网关节点处理器。"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from app.application.execution.bpmn_graph import ExecutionGraph, ExecutionNode
from app.application.execution.condition_evaluator import (
    evaluate_condition_rules,
    parse_condition_item,
)
from app.application.execution.execution_context import ExecutionContext


async def run_condition_node(
    node: ExecutionNode,
    ctx: ExecutionContext,
    graph: ExecutionGraph,
) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    """求值条件并标记未选分支首节点为 skipped。"""
    ctx.mark_node(node.id, node.type, "running")
    yield (
        "plan_update",
        {
            "step_id": node.id,
            "node_id": node.id,
            "node_type": node.type,
            "status": "running",
        },
    )

    raw_conditions = node.data.get("conditions")
    rules = []
    if isinstance(raw_conditions, list):
        for item in raw_conditions:
            if not isinstance(item, dict):
                continue
            rule = parse_condition_item(item)
            if rule is not None:
                rules.append(rule)

    matched_key, error = evaluate_condition_rules(
        rules,
        ctx.get_path,
        last_task_node_id=ctx.last_task_node_id,
    )
    if error or not matched_key:
        ctx.mark_node(node.id, node.type, "error")
        yield (
            "plan_update",
            {
                "step_id": node.id,
                "node_id": node.id,
                "node_type": node.type,
                "status": "error",
            },
        )
        yield ("error", {"message": error or "条件求值失败"})
        return

    # else 支：若图上无 else 出边则视为错误
    if matched_key == "else" and graph.successor_by_port(node.id, "else") is None:
        ctx.mark_node(node.id, node.type, "error")
        yield (
            "plan_update",
            {
                "step_id": node.id,
                "node_id": node.id,
                "node_type": node.type,
                "status": "error",
            },
        )
        yield ("error", {"message": "无匹配条件且缺少 else 分支"})
        return

    for target_id in graph.unselected_branch_targets(node.id, matched_key):
        target = graph.nodes.get(target_id)
        if target is None:
            continue
        ctx.mark_node(
            target_id,
            target.type,
            "skipped",
            skip_reason="条件未匹配",
        )
        payload: dict[str, Any] = {
            "step_id": target_id,
            "node_id": target_id,
            "node_type": target.type,
            "status": "skipped",
            "skipReason": "条件未匹配",
        }
        if target.data.get("tool"):
            payload["tool"] = target.data.get("tool")
        yield ("plan_update", payload)

    ctx.mark_node(
        node.id,
        node.type,
        "done",
        matched_branch_key=matched_key,
    )
    yield (
        "plan_update",
        {
            "step_id": node.id,
            "node_id": node.id,
            "node_type": node.type,
            "status": "done",
            "matchedBranchKey": matched_key,
        },
    )
