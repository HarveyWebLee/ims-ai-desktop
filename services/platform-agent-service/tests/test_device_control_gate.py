"""设备控制 HITL 门控单测（父图 device_gate）。"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.application.conversation.chat import stream_chat_core
from app.graph.context import AgentContext
from app.persistence.bootstrap import init_persistence
from app.services.device_control_gate import (
    parse_device_control_action,
    prepare_device_control_hitl_gate,
)


@pytest.fixture(autouse=True)
async def _memory_persistence():
    await init_persistence(None)


class TestParseDeviceControlAction:
    def test_broadcast(self):
        assert parse_device_control_action("广播") == "播报"

    def test_open_door(self):
        assert parse_device_control_action("开门") == "开门"

    def test_generic_dispatch_no_default_door(self):
        """通用「下发指令」不得默认成开门。"""
        assert parse_device_control_action("给设备下发指令") == ""
        assert parse_device_control_action("下发指令") == ""
        assert parse_device_control_action("指令下发") == ""
        assert parse_device_control_action("控制设备") == ""

    def test_conditional_skips(self):
        assert parse_device_control_action("如果在线就开门") is None
        assert parse_device_control_action("查716门禁，在线开门，离线查历史") is None

    def test_non_control(self):
        assert parse_device_control_action("查近三天告警") is None


class TestPrepareDeviceControlHitlGate:
    def test_broadcast_missing_device(self):
        ctx = AgentContext(thread_id="t1", message="广播", llm_user_message="广播")
        gate = prepare_device_control_hitl_gate(ctx)
        assert gate is not None
        assert gate.action == "播报"
        assert gate.interrupt_payload["type"] == "ask_params"
        assert gate.interrupt_payload["tool"] == "send_device_cmd"
        assert any(
            f.get("type") == "device_picker" for f in gate.interrupt_payload.get("fields") or []
        )

    def test_generic_dispatch_asks_device_and_variable(self):
        ctx = AgentContext(
            thread_id="t-generic",
            message="给设备下发指令",
            llm_user_message="给设备下发指令",
        )
        gate = prepare_device_control_hitl_gate(ctx)
        assert gate is not None
        assert gate.action == ""
        assert "action" not in gate.tool_args or not gate.tool_args.get("action")
        assert gate.interrupt_payload["type"] == "ask_params"
        fields = gate.interrupt_payload.get("fields") or []
        assert any(f.get("type") == "device_picker" for f in fields)
        assert any(f.get("type") == "variable_picker" for f in fields)
        assert any(f.get("name") == "variable_name" for f in fields)
        msg = str(gate.interrupt_payload.get("message") or "")
        assert "任意" in msg or "可写" in msg or "不限于" in msg

    def test_instruction_dispatch_alias_same_as_generic(self):
        """「指令下发」与「下发指令」同走通用设备控制门控。"""
        ctx = AgentContext(
            thread_id="t-alias",
            message="指令下发",
            llm_user_message="指令下发",
        )
        gate = prepare_device_control_hitl_gate(ctx)
        assert gate is not None
        assert gate.action == ""
        assert gate.interrupt_payload["type"] == "ask_params"
        assert gate.interrupt_payload["tool"] == "send_device_cmd"
        fields = gate.interrupt_payload.get("fields") or []
        assert any(f.get("type") == "device_picker" for f in fields)
        assert any(f.get("type") == "variable_picker" for f in fields)

    def test_complete_resolution_skips_gate(self):
        ctx = AgentContext(thread_id="t1", message="开门", llm_user_message="开门")
        with patch("contracts.device_command_resolver.resolve_device_command") as mock_resolve:
            mock_resolve.return_value.is_complete.return_value = True
            mock_resolve.return_value.interrupt = None
            mock_resolve.return_value.to_tool_args.return_value = {
                "device_code": "D1",
                "action": "开门",
            }
            assert prepare_device_control_hitl_gate(ctx) is None

    def test_conditional_control_skips_gate(self):
        ctx = AgentContext(
            thread_id="t1",
            message="如果在线就开门",
            llm_user_message="如果在线就开门",
        )
        assert prepare_device_control_hitl_gate(ctx) is None


class TestStreamChatDeviceControlGate:
    @pytest.mark.asyncio
    async def test_broadcast_emits_ask_params_via_parent_stream(self):
        thread_id = "device-gate-broadcast"
        events: list[tuple[str, dict]] = []

        async def fake_stream(**_kwargs):
            yield (
                "interrupt",
                {
                    "type": "ask_params",
                    "tool": "send_device_cmd",
                    "message": "请选择广播设备",
                    "fields": [{"type": "device_picker"}],
                },
            )
            yield ("done", {"type": "done", "thread_id": thread_id})

        with (
            patch("app.models.router.require_model_credentials"),
            patch(
                "app.graph.parent_graph_stream.stream_parent_graph",
                side_effect=fake_stream,
            ),
        ):
            async for evt in stream_chat_core(
                thread_id=thread_id,
                model_id="qwen3.7-plus",
                message="广播",
                metadata={},
            ):
                events.append(evt)

        assert not any(e[0] == "error" for e in events)
        intr = next(e[1] for e in events if e[0] == "interrupt")
        assert intr["type"] == "ask_params"
        assert intr["tool"] == "send_device_cmd"
        assert "广播设备" in intr["message"]
        assert events[-1][0] == "done"

    @pytest.mark.asyncio
    async def test_plan_confirm_emits_via_parent_stream(self):
        thread_id = "device-gate-plan-priority"
        events: list[tuple[str, dict]] = []

        async def fake_stream(**_kwargs):
            yield (
                "interrupt",
                {
                    "type": "plan_confirm",
                    "tool": "__plan__",
                    "steps": [
                        {"id": "1", "tool": "query_alarms"},
                        {"id": "2", "tool": "download_file"},
                    ],
                },
            )
            yield ("done", {"type": "done", "thread_id": thread_id})

        with (
            patch("app.models.router.require_model_credentials"),
            patch(
                "app.graph.parent_graph_stream.stream_parent_graph",
                side_effect=fake_stream,
            ),
        ):
            async for evt in stream_chat_core(
                thread_id=thread_id,
                model_id="qwen3.7-plus",
                message="查近三天告警然后导出",
                metadata={},
            ):
                events.append(evt)

        assert any(e[0] == "interrupt" and e[1].get("type") == "plan_confirm" for e in events)
        assert any(e[0] == "plan" for e in events)
