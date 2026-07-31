"""AC-35：LLM / validate 失败时静默回退 D1，并写入 bpmn_compile 可观测事件。"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.services.flow_ir import FlowIr, FlowIrCondition, FlowIrTaskNode
from app.services.llm_flow_compiler import try_compile_conditional_plan


def _door_ir() -> FlowIr:
    return FlowIr(
        entry="step_query",
        nodes=[
            FlowIrTaskNode(id="step_query", tool="get_device_detail", label="查"),
            FlowIrTaskNode(id="step_open", tool="send_device_cmd", label="开"),
            FlowIrTaskNode(
                id="step_vars",
                tool="query_device_variables",
                label="变量",
            ),
        ],
        conditions=[
            FlowIrCondition(
                id="cond",
                label="在线?",
                left="onlineStatus",
                operator="eq",
                right="在线",
                then_target="step_open",
                else_target="step_vars",
            )
        ],
    )


@pytest.mark.asyncio
async def test_ac35_validate_failed_falls_back_and_records_compile():
    """校验失败 → None（D1）+ bpmn_compile fallback=d1。"""
    recorded: list[dict] = []

    def _capture(**kwargs):
        recorded.append(kwargs)

    with (
        patch(
            "app.services.llm_flow_compiler.is_llm_flow_compile_enabled",
            return_value=True,
        ),
        patch(
            "app.services.llm_flow_compiler.generate_flow_ir",
            new=AsyncMock(return_value=_door_ir()),
        ),
        patch(
            "app.services.bpmn_orchestration.validate_flow_document",
            return_value={"valid": False, "errors": ["mock_invalid"]},
        ),
        patch(
            "app.services.bpmn_observability.record_bpmn_compile",
            side_effect=_capture,
        ),
    ):
        result = await try_compile_conditional_plan(
            "查门禁在线开门离线查历史",
            model_id="deepseek-v4-flash",
        )

    assert result is None
    assert recorded
    assert recorded[-1]["ok"] is False
    assert recorded[-1]["fallback"] == "d1"
    assert recorded[-1]["reason"] == "validate_failed"


@pytest.mark.asyncio
async def test_ac35_ir_none_falls_back_quietly():
    """IR 为空 → None，不抛错。"""
    recorded: list[dict] = []

    with (
        patch(
            "app.services.llm_flow_compiler.is_llm_flow_compile_enabled",
            return_value=True,
        ),
        patch(
            "app.services.llm_flow_compiler.generate_flow_ir",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "app.services.bpmn_observability.record_bpmn_compile",
            side_effect=lambda **kw: recorded.append(kw),
        ),
    ):
        result = await try_compile_conditional_plan("你好", model_id="deepseek-v4-flash")

    assert result is None
    assert recorded[-1]["fallback"] == "d1"
    assert "ir_none" in recorded[-1]["reason"]


@pytest.mark.asyncio
async def test_compile_disabled_records_disabled_fallback():
    """双灰度未开 → disabled。"""
    recorded: list[dict] = []

    with (
        patch(
            "app.services.llm_flow_compiler.is_llm_flow_compile_enabled",
            return_value=False,
        ),
        patch(
            "app.services.bpmn_observability.record_bpmn_compile",
            side_effect=lambda **kw: recorded.append(kw),
        ),
    ):
        result = await try_compile_conditional_plan("任意", model_id="x")

    assert result is None
    assert recorded[-1]["fallback"] == "disabled"
