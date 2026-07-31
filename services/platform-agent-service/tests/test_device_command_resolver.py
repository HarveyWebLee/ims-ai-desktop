"""设备指令 Resolver 单测"""

from __future__ import annotations

from unittest.mock import patch

from platform_mcp.runtime.device_action_catalog import (
    find_device_action_hint,
    infer_value_from_action,
    load_device_action_catalog,
)
from platform_mcp.runtime.device_command_resolver import (
    _pick_device_by_score,
    _score_device_match,
    pick_alternate_writable_variable,
    resolve_device_command,
)


class TestDeviceActionCatalog:
    def setup_method(self):
        load_device_action_catalog.cache_clear()

    def test_find_open_door(self):
        hint = find_device_action_hint("开门")
        assert hint is not None
        assert hint.get("action") == "开门"
        assert hint.get("requiredVarName") == "status_door_control"

    def test_infer_open_value(self):
        assert infer_value_from_action("开门") == "1"

    def test_infer_close_value(self):
        assert infer_value_from_action("关门") == "0"


class TestDeviceScoring:
    def test_exact_name_match(self):
        score = _score_device_match(
            "B口门禁",
            {"deviceName": "B口门禁", "deviceCode": "D1"},
        )
        assert score >= 95

    def test_top1_auto_select(self):
        records = [
            {"deviceName": "B口门禁", "deviceCode": "D1"},
            {"deviceName": "A口门禁", "deviceCode": "D2"},
            {"deviceName": "C口门禁", "deviceCode": "D3"},
        ]
        picked, _, auto = _pick_device_by_score("B口门禁", records)
        assert auto is True
        assert picked is not None
        assert picked["deviceCode"] == "D1"

    def test_ambiguous_no_auto_select(self):
        records = [
            {"deviceName": "1号门禁", "deviceCode": "D1"},
            {"deviceName": "2号门禁", "deviceCode": "D2"},
        ]
        picked, _, auto = _pick_device_by_score("门禁", records)
        assert auto is False
        assert picked is None


class TestDoorControlBinding:
    """开门/关门硬绑定 status_door_control（方案 A）。"""

    def setup_method(self):
        load_device_action_catalog.cache_clear()

    @patch("platform_mcp.runtime.device_command_resolver._fetch_device_variable_records")
    @patch("platform_mcp.runtime.device_command_resolver._resolve_device_with_auto_select")
    def test_full_resolution_binds_status_door_control(
        self,
        mock_resolve_device,
        mock_fetch_vars,
    ):
        mock_resolve_device.return_value = (
            "D1",
            {"deviceCode": "D1", "deviceName": "B口门禁"},
            None,
            True,
        )
        mock_fetch_vars.return_value = [
            {"varName": "switch", "showName": "开关", "isWrite": 1},
            {"varName": "status_door_open", "showName": "开门状态", "isWrite": 1},
            {"varName": "status_door_control", "showName": "门控制状态", "isWrite": 1},
        ]

        res = resolve_device_command(
            device_name="B口门禁",
            action="开门",
        )
        assert res.is_complete()
        assert res.device_code == "D1"
        assert res.variable_name == "status_door_control"
        assert res.variable_value == "1"
        assert "device" in res.auto_resolved
        assert "variable" in res.auto_resolved
        assert "value" in res.auto_resolved

    @patch("platform_mcp.runtime.device_command_resolver._fetch_device_variable_records")
    @patch("platform_mcp.runtime.device_command_resolver._resolve_device_with_auto_select")
    def test_close_door_writes_zero(
        self,
        mock_resolve_device,
        mock_fetch_vars,
    ):
        mock_resolve_device.return_value = (
            "D1",
            {"deviceCode": "D1", "deviceName": "B口门禁"},
            None,
            True,
        )
        mock_fetch_vars.return_value = [
            {"varName": "status_door_control", "showName": "门控制状态", "isWrite": 1},
        ]

        res = resolve_device_command(device_code="D1", action="关门")
        assert res.is_complete()
        assert res.variable_name == "status_door_control"
        assert res.variable_value == "0"

    @patch("platform_mcp.runtime.device_command_resolver._fetch_device_variable_records")
    @patch("platform_mcp.runtime.device_command_resolver._resolve_device_with_auto_select")
    def test_missing_door_control_hard_fail(
        self,
        mock_resolve_device,
        mock_fetch_vars,
    ):
        mock_resolve_device.return_value = (
            "D1",
            {"deviceCode": "D1", "deviceName": "空调1"},
            None,
            True,
        )
        # 仅有其它门相关变量，无 status_door_control → 硬失败
        mock_fetch_vars.return_value = [
            {"varName": "status_door_open", "showName": "开门状态", "isWrite": 1},
            {"varName": "switch", "showName": "开关", "isWrite": 1},
        ]

        res = resolve_device_command(device_name="空调1", action="开门")
        assert not res.is_complete()
        assert "variable" in res.missing
        assert res.interrupt is not None
        assert res.interrupt.get("fields") == []
        assert "status_door_control" in str(res.interrupt.get("message") or "")

    @patch("platform_mcp.runtime.device_command_resolver._fetch_device_variable_records")
    @patch("platform_mcp.runtime.device_command_resolver._resolve_device_with_auto_select")
    def test_ignores_other_variable_name_when_door_action(
        self,
        mock_resolve_device,
        mock_fetch_vars,
    ):
        mock_resolve_device.return_value = (
            "D1",
            {"deviceCode": "D1", "deviceName": "B口门禁"},
            None,
            True,
        )
        mock_fetch_vars.return_value = [
            {"varName": "status_door_open", "showName": "开门状态", "isWrite": 1},
            {"varName": "status_door_control", "showName": "门控制状态", "isWrite": 1},
        ]

        res = resolve_device_command(
            device_code="D1",
            action="开门",
            variable_name="status_door_open",
        )
        assert res.is_complete()
        assert res.variable_name == "status_door_control"

    @patch("platform_mcp.runtime.device_command_resolver._fetch_device_variable_records")
    def test_no_alternate_retry_for_door_action(self, mock_fetch_vars):
        mock_fetch_vars.return_value = [
            {"varName": "status_door_control", "showName": "门控制状态", "isWrite": 1},
            {"varName": "status_door_open", "showName": "开门状态", "isWrite": 1},
        ]
        alt_vn, _ = pick_alternate_writable_variable(
            "D1",
            exclude_var="status_door_control",
            action="开门",
        )
        assert alt_vn is None


class TestBroadcastPlayBinding:
    """播报硬绑定 play，正文须明确（方案同门控 A）。"""

    def setup_method(self):
        load_device_action_catalog.cache_clear()

    def test_find_broadcast_action(self):
        hint = find_device_action_hint("播报")
        assert hint is not None
        assert hint.get("requiredVarName") == "play"
        assert hint.get("requireUserValue") is True

        hint2 = find_device_action_hint("下发广播")
        assert hint2 is not None
        assert hint2.get("action") == "播报"

    def test_extract_content_from_utterance(self):
        from platform_mcp.runtime.device_action_catalog import extract_user_value_from_text

        assert extract_user_value_from_text("播报", user_text="播报请注意安全") == "请注意安全"
        assert extract_user_value_from_text("播报紧急疏散") == "紧急疏散"
        assert extract_user_value_from_text("广播", user_text="广播火灾疏散内容") == "火灾疏散"
        assert extract_user_value_from_text("播报") is None

    @patch("platform_mcp.runtime.device_command_resolver._fetch_device_variable_records")
    @patch("platform_mcp.runtime.device_command_resolver._resolve_device_with_auto_select")
    def test_broadcast_with_content(
        self,
        mock_resolve_device,
        mock_fetch_vars,
    ):
        mock_resolve_device.return_value = (
            "B1",
            {"deviceCode": "B1", "deviceName": "大厅广播"},
            None,
            True,
        )
        mock_fetch_vars.return_value = [
            {"varName": "volume", "showName": "音量", "isWrite": 1},
            {"varName": "play", "showName": "播报", "isWrite": 1},
        ]

        res = resolve_device_command(
            device_name="大厅广播",
            action="播报",
            variable_value="请注意安全",
        )
        assert res.is_complete()
        assert res.variable_name == "play"
        assert res.variable_value == "请注意安全"

    @patch("platform_mcp.runtime.device_command_resolver._fetch_device_variable_records")
    @patch("platform_mcp.runtime.device_command_resolver._resolve_device_with_auto_select")
    def test_broadcast_extracts_content_from_action(
        self,
        mock_resolve_device,
        mock_fetch_vars,
    ):
        mock_resolve_device.return_value = (
            "B1",
            {"deviceCode": "B1", "deviceName": "大厅广播"},
            None,
            True,
        )
        mock_fetch_vars.return_value = [
            {"varName": "play", "showName": "播报", "isWrite": 1},
        ]

        res = resolve_device_command(
            device_code="B1",
            action="播报请疏散",
        )
        assert res.is_complete()
        assert res.variable_name == "play"
        assert res.variable_value == "请疏散"

    @patch("platform_mcp.runtime.device_command_resolver._fetch_device_variable_records")
    @patch("platform_mcp.runtime.device_command_resolver._resolve_device_with_auto_select")
    def test_broadcast_missing_content_hitl(
        self,
        mock_resolve_device,
        mock_fetch_vars,
    ):
        mock_resolve_device.return_value = (
            "B1",
            {"deviceCode": "B1", "deviceName": "大厅广播"},
            None,
            True,
        )
        mock_fetch_vars.return_value = [
            {"varName": "play", "showName": "播报", "isWrite": 1},
        ]

        res = resolve_device_command(device_code="B1", action="播报")
        assert not res.is_complete()
        assert "value" in res.missing
        assert res.interrupt is not None
        fields = res.interrupt.get("fields") or []
        assert any(f.get("name") == "variable_value" for f in fields)
        assert any(f.get("label") == "播报内容" for f in fields)
        assert "播报" in str(res.interrupt.get("message") or "")

    @patch("platform_mcp.runtime.device_command_resolver._fetch_device_variable_records")
    @patch("platform_mcp.runtime.device_command_resolver._resolve_device_with_auto_select")
    def test_missing_play_hard_fail(
        self,
        mock_resolve_device,
        mock_fetch_vars,
    ):
        mock_resolve_device.return_value = (
            "D1",
            {"deviceCode": "D1", "deviceName": "空调1"},
            None,
            True,
        )
        mock_fetch_vars.return_value = [
            {"varName": "switch", "showName": "开关", "isWrite": 1},
        ]

        res = resolve_device_command(
            device_code="D1",
            action="播报",
            variable_value="测试",
        )
        assert not res.is_complete()
        assert res.interrupt is not None
        assert res.interrupt.get("fields") == []
        assert "play" in str(res.interrupt.get("message") or "")

    @patch("platform_mcp.runtime.device_command_resolver._fetch_device_variable_records")
    def test_no_alternate_retry_for_broadcast(self, mock_fetch_vars):
        mock_fetch_vars.return_value = [
            {"varName": "play", "showName": "播报", "isWrite": 1},
            {"varName": "tts", "showName": "语音", "isWrite": 1},
        ]
        alt_vn, _ = pick_alternate_writable_variable(
            "B1",
            exclude_var="play",
            action="播报",
        )
        assert alt_vn is None


class TestResolveDeviceCommand:
    def setup_method(self):
        load_device_action_catalog.cache_clear()

    @patch("platform_mcp.runtime.device_command_resolver.call_platform_api")
    def test_missing_device_interrupt(self, mock_api):
        res = resolve_device_command(action="开门")
        assert "device" in res.missing
        assert res.interrupt is not None
        assert res.interrupt.get("type") == "ask_params"
        fields = res.interrupt.get("fields") or []
        assert any(f.get("type") == "device_picker" for f in fields)
        assert any(f.get("name") == "device_code" for f in fields)

    @patch("platform_mcp.runtime.device_command_resolver.call_platform_api")
    def test_missing_device_generic_uses_variable_picker(self, mock_api):
        """通用下发：同屏设备表格 + 变量下拉（不再用手填动作文本）。"""
        res = resolve_device_command()
        assert "device" in res.missing
        assert res.interrupt is not None
        fields = res.interrupt.get("fields") or []
        assert any(f.get("type") == "device_picker" for f in fields)
        assert any(f.get("type") == "variable_picker" for f in fields)
        assert any(f.get("name") == "variable_name" for f in fields)
        assert not any(f.get("name") == "action" for f in fields)

    @patch("platform_mcp.runtime.device_command_resolver.call_platform_api")
    def test_missing_device_broadcast_message(self, mock_api):
        res = resolve_device_command(action="播报")
        assert res.interrupt is not None
        assert "广播" in str(res.interrupt.get("message") or "")
        fields = res.interrupt.get("fields") or []
        assert any(f.get("type") == "device_picker" for f in fields)
        # 无正文时同屏补播报内容
        assert any(f.get("name") == "variable_value" for f in fields)
