"""AC-36：关 AGENT_BPMN_LLM_COMPILE 时门控不走 IR，条件句不产出 CONDITION 画布。"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.graph.context import AgentContext
from app.services.plan_confirm import prepare_plan_confirm_gate_async


def _ctx(message: str) -> AgentContext:
    return AgentContext(
        thread_id="t-ac36",
        message=message,
        llm_user_message=message,
        metadata={},
    )


@pytest.mark.asyncio
async def test_ac36_gate_skips_try_compile_when_llm_flag_off():
    """CONDITION_EXEC 开、LLM_COMPILE 关：不调用 try_compile_conditional_plan。"""
    try_compile = AsyncMock(return_value=MagicMock())

    with (
        patch(
            "app.services.llm_flow_compiler.is_llm_flow_compile_enabled",
            return_value=False,
        ),
        patch(
            "app.services.llm_flow_compiler.try_compile_conditional_plan",
            new=try_compile,
        ),
        patch(
            "app.services.plan_route.evaluate_plan_route",
            return_value=MagicMock(),
        ) as mock_route,
    ):
        # 非 EXPLICIT_PLAN → 直接 None，且未调用 compile
        from app.services.plan_route import PlanExecutionMode

        mock_route.return_value = PlanExecutionMode.REACT
        gate = await prepare_plan_confirm_gate_async(
            _ctx("查716门禁状态，在线开门，离线查历史"),
            model_id="deepseek-v4-flash",
        )

    assert gate is None
    try_compile.assert_not_called()


@pytest.mark.asyncio
async def test_ac36_gate_falls_to_d1_without_flow_document():
    """关编译时即便 resolve 出线性 Plan，也不带 flow_document（无 CONDITION）。"""
    linear_steps = [
        {
            "id": "1",
            "label": "查设备",
            "tool": "get_device_detail",
            "status": "pending",
        },
        {
            "id": "2",
            "label": "开门",
            "tool": "send_device_cmd",
            "status": "pending",
        },
    ]

    with (
        patch(
            "app.services.llm_flow_compiler.is_llm_flow_compile_enabled",
            return_value=False,
        ),
        patch(
            "app.services.llm_flow_compiler.try_compile_conditional_plan",
            new=AsyncMock(),
        ) as try_compile,
        patch(
            "app.services.plan_route.evaluate_plan_route",
        ) as mock_route,
        patch(
            "app.services.llm_task_planner.resolve_task_plan",
            new=AsyncMock(return_value=linear_steps),
        ),
        patch(
            "app.services.plan_confirm.settings",
        ) as mock_settings,
    ):
        from app.services.plan_route import PlanExecutionMode

        mock_route.return_value = PlanExecutionMode.EXPLICIT_PLAN
        mock_settings.agent_plan_confirm_enabled = True
        mock_settings.agent_plan_confirm_write_only = False
        mock_settings.agent_llm_plan_params_enabled = False

        gate = await prepare_plan_confirm_gate_async(
            _ctx("查设备然后开门"),
            model_id="deepseek-v4-flash",
        )

    try_compile.assert_not_called()
    assert gate is not None
    flow = gate.interrupt_payload.get("flow_document") or {}
    assert not any(
        str(n.get("type") or "").upper() == "CONDITION"
        for n in (flow.get("nodes") or [])
        if isinstance(n, dict)
    )
    assert gate.resume_hint.get("compile_source") != "llm_ir"
