"""
Plan 路由决策（生产化收敛）。

文件职责
--------
用**同步、不调 LLM**的规则，决定本轮消息走哪条执行轨道：
  - ``EXPLICIT_PLAN``：显式多步 Plan + plan_confirm 门控 → 再 execute_plan_steps
  - ``REACT``：交给 ReAct / PlanTracker 动态对齐（单步、只读多步、非复合等）

这是运行时**唯一**「要不要上 plan_confirm」的快速入口，避免对 ReAct 路径
无谓调用 ``resolve_task_plan``（LLM Plan）拖慢首包 SSE。

决策表（与 docs/architecture/03-agent-runtime.md 一致）
------------------------------------------------
    - classify → CHAT：chat_direct（本模块不涉及）
    - LLM/规则多步 + plan_needs_user_confirm → 显式 Plan + plan_confirm
    - 其余（单步、只读多步、非复合）→ ReAct + PlanTracker

在 Agent 流程中的位置
--------------------
    prepare_plan_confirm_gate_async
      → evaluate_plan_route(message)
      → EXPLICIT_PLAN：resolve_task_plan → prepare_plan_confirm_gate
      → REACT：直接返回 None，builder 走 ReAct

如何被调用
----------
- 主要：``app.services.plan_confirm.prepare_plan_confirm_gate_async``
- 依赖：``task_planner.build_task_plan``、``plan_confirm.plan_needs_user_confirm``
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from app.config import settings
from app.services.plan_confirm import plan_needs_user_confirm
from app.services.task_planner import build_task_plan


class PlanExecutionMode(StrEnum):
    """
    Plan 执行模式枚举。

    - REACT：模型边想边调工具，PlanTracker 事后对齐步骤条
    - EXPLICIT_PLAN：先出完整步骤给用户确认，再按序执行
    """

    REACT = "react"
    EXPLICIT_PLAN = "explicit_plan"


def _normalize_rule_steps(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """过滤无 tool 的规则步骤，并补齐 id/label/status 字段。"""
    steps: list[dict[str, Any]] = []
    for i, step in enumerate(raw, 1):
        tool = step.get("tool")
        if not tool:
            continue
        steps.append(
            {
                "id": str(step.get("id") or i),
                "label": str(step.get("label") or tool),
                "tool": str(tool),
                "status": str(step.get("status") or "pending"),
            }
        )
    return steps


def evaluate_plan_route(
    message: str,
    *,
    metadata: dict[str, Any] | None = None,
) -> PlanExecutionMode:
    """
    同步决策：当前消息是否应走显式 Plan + plan_confirm。

    规则层快速预判（不调用 LLM）
    ----------------------------
    1. ``agent_plan_confirm_enabled`` 关闭 → ReAct
    2. 规则 ``build_task_plan`` 不足 2 步 → ReAct（单步 / 非复合）
    3. 多步但 ``plan_needs_user_confirm`` 为 False（如只读多步）→ ReAct
    4. 其余 → 显式 Plan（后续 async 路径再 ``resolve_task_plan``）

    说明：P2 条件图由 ``prepare_plan_confirm_gate_async`` 优先调 LLM IR 判定，
    本函数不再用正则强制 EXPLICIT_PLAN。
    """
    if not settings.agent_plan_confirm_enabled:
        return PlanExecutionMode.REACT

    rule_plan = build_task_plan(message, metadata=metadata)
    if not rule_plan or len(rule_plan) < 2:
        return PlanExecutionMode.REACT

    steps = _normalize_rule_steps(rule_plan)
    if len(steps) < 2:
        return PlanExecutionMode.REACT

    # write_only 等策略：纯查询+导航可跳过门控；含导出/批量写则必须确认
    if not plan_needs_user_confirm(steps):
        mode = PlanExecutionMode.REACT
    else:
        mode = PlanExecutionMode.EXPLICIT_PLAN

    from contracts.agent_debug import agent_debug, summarize_plan_steps

    agent_debug(
        "flow.plan.route_eval",
        message_preview=(message or "")[:80],
        mode=str(mode),
        rule_plan=summarize_plan_steps(steps),
    )
    return mode
