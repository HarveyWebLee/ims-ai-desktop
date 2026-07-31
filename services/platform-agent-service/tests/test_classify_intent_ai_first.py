"""classify 意图路由：AGENT_INTENT_AI_FIRST 双路径单测。"""

from __future__ import annotations

from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.graph.parent_graph import ParentState, classify_node


def _state(message: str) -> ParentState:
    return cast(
        ParentState,
        {
            "user_message": message,
            "llm_user_message": message,
            "model_id": "qwen3.7-plus",
            "metadata": {},
            "messages": [],
        },
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "message",
    [
        "给 icpas101 播放广播，内容为你好",
        "下发指令",
        "指令下发",
        "开门",
        "你好",
        "广播",
    ],
)
async def test_ai_first_always_routes_react(message: str):
    """开启 AI 优先时，classify 恒出 react，不进门控。"""
    with patch("app.config.settings") as mock_settings:
        mock_settings.agent_intent_ai_first = True
        with (
            patch(
                "app.services.plan_confirm.prepare_plan_confirm_gate_async",
                new_callable=AsyncMock,
            ) as mock_plan,
            patch(
                "app.services.device_control_gate.prepare_device_control_hitl_gate",
            ) as mock_device,
        ):
            result = await classify_node(_state(message))
            assert result == {"route": "react"}
            mock_plan.assert_not_called()
            mock_device.assert_not_called()


@pytest.mark.asyncio
async def test_gates_enabled_greeting_routes_chat_direct():
    """关闭 AI 优先时，寒暄仍走 chat_direct。"""
    with patch("app.config.settings") as mock_settings:
        mock_settings.agent_intent_ai_first = False
        result = await classify_node(_state("你好"))
        assert result == {"route": "chat_direct"}


@pytest.mark.asyncio
async def test_gates_enabled_device_control_routes_device_gate():
    """关闭 AI 优先时，缺槽设备控制仍走 device_gate。"""
    fake_gate = MagicMock()
    fake_gate.interrupt_payload = {
        "type": "ask_params",
        "tool": "send_device_cmd",
        "message": "请选择广播设备",
        "fields": [{"type": "device_picker"}],
    }
    fake_gate.tool_args = {"action": "播报"}

    with patch("app.config.settings") as mock_settings:
        mock_settings.agent_intent_ai_first = False
        with (
            patch(
                "app.services.plan_confirm.prepare_plan_confirm_gate_async",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.device_control_gate.prepare_device_control_hitl_gate",
                return_value=fake_gate,
            ),
        ):
            result = await classify_node(_state("广播"))
            assert result["route"] == "device_gate"
            assert result["device_interrupt_payload"]["tool"] == "send_device_cmd"
            assert result["device_tool_args"]["action"] == "播报"


@pytest.mark.asyncio
async def test_gates_enabled_no_gate_routes_react():
    """关闭 AI 优先且无门控命中时，仍走 react。"""
    with patch("app.config.settings") as mock_settings:
        mock_settings.agent_intent_ai_first = False
        with (
            patch(
                "app.services.plan_confirm.prepare_plan_confirm_gate_async",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.device_control_gate.prepare_device_control_hitl_gate",
                return_value=None,
            ),
        ):
            result = await classify_node(_state("查近三天告警"))
            assert result == {"route": "react"}
