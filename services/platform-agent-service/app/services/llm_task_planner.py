"""
Phase D1：LLM 显式任务规划。

文件职责
--------
在 plan_confirm 门控前，用 LLM structured output 生成「多步 Plan」
（步骤 id / 使用者视角 label / catalog 工具名）。
与规则 ``build_task_plan`` 互补：规则够用则不去调 LLM；失败则回退规则。

在 Agent 流程中的位置
--------------------
    evaluate_plan_route → EXPLICIT_PLAN
      → resolve_task_plan（本模块对外主入口）
          1) 规则 Plan ≥2 步 → 直接返回（快出 SSE）
          2) 不够再 generate_llm_task_plan
      → prepare_plan_confirm_gate → interrupt plan_confirm

白话解释
--------
复杂需求（查+导出+跳转）需要一张步骤清单给用户点「确认」。
规则模板能匹配常见句式；匹配不上时再请模型拆步骤。
单步结果视为无效显式 Plan（返回 None 或不足 2 步），避免无谓门控。

如何被调用
----------
- ``plan_confirm.prepare_plan_confirm_gate_async`` → ``resolve_task_plan``
- 开关：``settings.agent_llm_plan_enabled``
- Prompt：``app/prompts/llm_plan.md``，工具清单来自 tool catalog
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


class LlmPlanStepOut(BaseModel):
    """LLM 输出的单步计划（structured output 一行）。"""

    id: str = Field(description="步骤序号，如 1、2")
    label: str = Field(description="使用者视角步骤描述")
    tool: str = Field(description="工具名，须为 catalog 已注册工具")


class LlmTaskPlanOut(BaseModel):
    """LLM 结构化 Plan 响应：steps 列表，最多 6 步。"""

    steps: list[LlmPlanStepOut] = Field(default_factory=list, max_length=6)


def _load_llm_plan_prompt() -> str:
    """读取 llm_plan.md 系统提示词。"""
    path = _PROMPTS_DIR / "llm_plan.md"
    return path.read_text(encoding="utf-8")


def _tool_list_for_prompt() -> str:
    """从 catalog 生成工具清单，注入规划 prompt（防止模型瞎编工具名）。"""
    from contracts.tool_catalog_loader import load_tool_catalog

    lines: list[str] = []
    for tool in load_tool_catalog():
        name = str(tool.get("name") or "")
        if not name:
            continue
        desc = str(tool.get("description") or "")[:60]
        lines.append(f"- `{name}`：{desc}")
    return "\n".join(lines) if lines else "- query_alarms\n- download_file\n- navigate_to"


def _allowed_tool_names() -> frozenset[str]:
    """当前已导出 catalog 中的合法工具名集合。"""
    from contracts.tool_catalog_loader import load_tool_catalog

    return frozenset(str(t["name"]) for t in load_tool_catalog() if t.get("name"))


def normalize_llm_plan_steps(raw_steps: list[LlmPlanStepOut]) -> list[dict[str, Any]]:
    """
    校验并规范化 LLM Plan 步骤。

    - 未知 tool：丢弃并打 warning
    - 每步补 ``status=pending``
    - label 截断到 48 字，避免侧栏过长
    """
    allowed = _allowed_tool_names()
    normalized: list[dict[str, Any]] = []
    for i, step in enumerate(raw_steps, 1):
        tool = (step.tool or "").strip()
        if tool not in allowed:
            logger.warning("LLM Plan 忽略未知工具: %s", tool)
            continue
        normalized.append(
            {
                "id": str(step.id or i),
                "label": (step.label or tool)[:48],
                "tool": tool,
                "status": "pending",
            }
        )
    return normalized


async def generate_llm_task_plan(
    message: str,
    *,
    metadata: dict[str, Any] | None = None,
    model_id: str,
) -> list[dict[str, Any]] | None:
    """
    调用 LLM 生成多步 Plan。

    返回 None 的情况（由调用方回退规则 Plan）
    --------------------------------------
    - 开关关闭 / mock
    - 空消息
    - 规范化后不足 2 步
    - 超时或调用异常

    参数
    ----
    message : str
        用户需求原话。
    metadata : dict | None
        预留页面上下文；当前实现未使用（显式 ``_ = metadata``）。
    model_id : str
        选用模型目录 id。
    """
    _ = metadata
    if not settings.agent_llm_plan_enabled:
        return None

    msg = (message or "").strip()
    if not msg:
        return None

    try:
        from app.models.router import resolve_chat_model
        from app.services.llm_structured_invoke import ainvoke_structured_with_timeout

        model = resolve_chat_model(model_id)
        structured = model.with_structured_output(LlmTaskPlanOut)

        system = _load_llm_plan_prompt().replace("{{TOOL_LIST}}", _tool_list_for_prompt())
        user_content = f"使用者需求：{msg}\n\n请输出 steps JSON。"

        from contracts.agent_debug import agent_debug, preview_text, summarize_plan_steps

        agent_debug(
            "flow.ai.llm_plan.request",
            model_id=model_id,
            user_prompt=preview_text(user_content, max_len=400),
            system_chars=len(system),
        )

        result: LlmTaskPlanOut = await ainvoke_structured_with_timeout(
            structured,
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            label="LLM Plan 生成",
        )
        steps = normalize_llm_plan_steps(result.steps)
        agent_debug(
            "flow.ai.llm_plan.response",
            model_id=model_id,
            raw_step_count=len(result.steps),
            llm_plan_steps=summarize_plan_steps(steps),
        )
        # 显式 Plan 至少 2 步才有门控意义；单步走 ReAct 即可
        if len(steps) < 2:
            return None
        logger.info(
            "LLM Plan 生成成功: steps=%s tools=%s",
            len(steps),
            [s["tool"] for s in steps],
        )
        return steps
    except Exception as exc:
        logger.warning("LLM Plan 生成失败，回退规则 Plan: %s", exc)
        return None


async def resolve_task_plan(
    message: str,
    *,
    metadata: dict[str, Any] | None = None,
    model_id: str | None = None,
) -> list[dict[str, Any]] | None:
    """
    显式 Plan 路径专用：规则优先，不足 2 步再调 LLM。

    设计用意
    --------
    门控前希望尽快吐出 SSE；规则命中则 ``skipped_llm=True``，不烧模型额度。
    调用方须先经 ``plan_route.evaluate_plan_route`` 判定为 ``EXPLICIT_PLAN``。

    返回
    ----
    list[dict] | None
        多步或规则不足时的规则结果（可能仍为单步/空，由上层再判）。
    """
    from app.services.task_planner import build_task_plan
    from contracts.agent_debug import agent_debug, summarize_plan_steps

    rule_steps = build_task_plan(message, metadata=metadata)
    if rule_steps and len(rule_steps) >= 2:
        agent_debug(
            "flow.plan.resolved",
            source="rule",
            plan_steps=summarize_plan_steps(rule_steps),
            skipped_llm=True,
        )
        return rule_steps

    if model_id and settings.agent_llm_plan_enabled:
        llm_steps = await generate_llm_task_plan(
            message,
            metadata=metadata,
            model_id=model_id,
        )
        if llm_steps and len(llm_steps) >= 2:
            agent_debug(
                "flow.plan.resolved",
                source="llm",
                plan_steps=summarize_plan_steps(llm_steps),
            )
            return llm_steps

    agent_debug(
        "flow.plan.resolved",
        source="rule",
        plan_steps=summarize_plan_steps(rule_steps) if rule_steps else [],
    )
    return rule_steps
