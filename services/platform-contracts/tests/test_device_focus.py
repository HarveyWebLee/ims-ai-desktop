"""设备焦点与会话上下文单测。"""

from __future__ import annotations

from contracts.context import current_device_focus
from contracts.device_focus import (
    DeviceFocus,
    apply_device_focus_to_interrupt,
    device_focus_from_tool_result,
)


class TestDeviceFocusFromToolResult:
    def test_query_devices_unique(self):
        focus = device_focus_from_tool_result(
            tool_name="query_devices",
            payload={
                "ok": True,
                "data": {
                    "total": 1,
                    "items": [{"deviceCode": "D1", "deviceName": "一门"}],
                    "queryContext": {"onlineStatus": 1},
                },
            },
        )
        assert focus is not None
        assert focus.is_unique
        assert focus.device_code == "D1"

    def test_query_devices_multi_keeps_filters(self):
        focus = device_focus_from_tool_result(
            tool_name="query_devices",
            payload={
                "ok": True,
                "data": {
                    "total": 1425,
                    "items": [{"deviceCode": "A"}, {"deviceCode": "B"}],
                    "queryContext": {"onlineStatus": 1},
                },
            },
        )
        assert focus is not None
        assert not focus.device_code
        assert focus.default_filters.get("onlineStatus") == 1
        assert "1425" in focus.hint_message

    def test_apply_filters_to_interrupt(self):
        focus = DeviceFocus(
            total=10,
            default_filters={"onlineStatus": 1},
            hint_message="请从在线设备中单选",
        )
        interrupt = apply_device_focus_to_interrupt(
            {
                "type": "ask_params",
                "message": "未指定设备",
                "fields": [{"type": "device_picker", "name": "device_code"}],
            },
            focus,
        )
        assert interrupt is not None
        field = interrupt["fields"][0]
        assert field["defaultFilters"]["onlineStatus"] == 1
        assert interrupt["message"] == "请从在线设备中单选"


class TestInferUsesUniqueFocus:
    def test_pronoun_uses_focus(self):
        from contracts.device_context import infer_device_token_from_conversation

        focus = DeviceFocus(device_code="HK191", device_name="海康摄像机", total=1)
        token = current_device_focus.set(focus)
        try:
            assert (
                infer_device_token_from_conversation(
                    "给这个设备下发指令", ["查询目前在线的设备列表"]
                )
                == "HK191"
            )
        finally:
            current_device_focus.reset(token)
