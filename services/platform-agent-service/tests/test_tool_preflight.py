"""Phase C3 统一 preflight 单测"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from contracts.tool_preflight import ensure_tool_args, preflight_tool


class TestPreflightTool:
    def test_query_alarms_missing_time(self):
        result = preflight_tool("query_alarms", {"start_time": "", "end_time": ""})
        assert result.interrupt is not None
        assert result.interrupt["type"] == "ask_params"
        assert result.interrupt["tool"] == "query_alarms"
        assert result.interrupt["fields"]

    def test_query_alarms_prefills_unique_device_focus(self):
        from contracts.context import current_device_focus
        from contracts.device_focus import DeviceFocus

        focus = DeviceFocus(
            device_code="zhonglian_9001",
            device_name="中联门禁",
            total=1,
            source_tool="get_device_detail",
        )
        token = current_device_focus.set(focus)
        try:
            result = preflight_tool("query_alarms", {"start_time": "", "end_time": ""})
        finally:
            current_device_focus.reset(token)
        assert result.interrupt is not None
        assert result.args.get("device_code") == "zhonglian_9001"
        assert result.interrupt.get("current", {}).get("device_code") == "zhonglian_9001"

    def test_query_alarms_with_relative_time(self):
        result = preflight_tool(
            "query_alarms",
            {"start_time": "近三天", "end_time": ""},
        )
        assert result.interrupt is None

    def test_download_file_missing_time(self):
        result = preflight_tool(
            "download_file",
            {"resource": "alarm_report", "start_time": "", "end_time": ""},
        )
        assert result.interrupt is not None
        assert result.interrupt["tool"] == "download_file"

    def test_download_file_sentry_handover_missing_time(self):
        result = preflight_tool(
            "download_file",
            {"resource": "sentry_handover", "start_time": "", "end_time": ""},
        )
        assert result.interrupt is not None
        assert result.interrupt["tool"] == "download_file"
        assert "岗哨交接" in result.interrupt["message"]
        field_names = [f["name"] for f in result.interrupt["fields"]]
        assert field_names == ["time_range"]

    def test_download_file_duty_info_missing_time(self):
        result = preflight_tool(
            "download_file",
            {"resource": "duty_info", "start_time": "", "end_time": ""},
        )
        assert result.interrupt is not None
        assert "值班信息" in result.interrupt["message"]

    def test_download_file_duty_manage_missing_time(self):
        result = preflight_tool(
            "download_file",
            {"resource": "duty_manage", "start_time": "", "end_time": ""},
        )
        assert result.interrupt is not None
        assert "值班管理" in result.interrupt["message"]

    def test_download_file_acs_record_missing_time(self):
        result = preflight_tool(
            "download_file",
            {"resource": "acs_record", "start_time": "", "end_time": ""},
        )
        assert result.interrupt is not None
        assert "出入信息" in result.interrupt["message"]

    def test_get_alarm_detail_missing_id(self):
        result = preflight_tool("get_alarm_detail", {})
        assert result.interrupt is not None
        assert result.interrupt["tool"] == "get_alarm_detail"

    def test_navigate_missing_path(self):
        result = preflight_tool("navigate_to", {"path": ""})
        assert result.interrupt is not None

    def test_open_alarm_detail_missing_id_via_catalog(self):
        """catalog required 驱动：open_alarm_detail 缺 alarm_id 时触发 HITL。"""
        result = preflight_tool("open_alarm_detail", {})
        assert result.interrupt is not None
        assert result.interrupt["tool"] == "open_alarm_detail"
        field_names = [f["name"] for f in result.interrupt["fields"]]
        assert "alarm_id" in field_names

    def test_batch_confirm_with_alarm_ids_skips_time(self):
        result = preflight_tool(
            "batch_confirm_alarms",
            {"alarm_ids": "A001,A002"},
        )
        assert result.interrupt is None

    def test_batch_confirm_missing_time_and_ids(self):
        result = preflight_tool("batch_confirm_alarms", {})
        assert result.interrupt is not None
        field_names = [f["name"] for f in result.interrupt["fields"]]
        assert "time_range" in field_names

    def test_get_device_detail_missing_one_of_params(self):
        """仅声明 one_of 的工具缺少全部候选参数时应触发统一 HITL。"""
        result = preflight_tool("get_device_detail", {})
        assert result.interrupt is not None
        assert result.interrupt["tool"] == "get_device_detail"
        field_names = [field["name"] for field in result.interrupt["fields"]]
        assert field_names == ["device_code", "device_name"]

    @pytest.mark.parametrize(
        ("args", "expected"),
        [
            ({"device_code": "D001"}, "D001"),
            ({"device_name": "一号泵"}, "一号泵"),
        ],
    )
    def test_get_device_detail_accepts_each_one_of_group(self, args, expected):
        result = preflight_tool("get_device_detail", args)
        assert result.interrupt is None
        assert expected in result.args.values()

    def test_query_device_variables_missing_one_of_params(self):
        """与 get_device_detail 对齐：缺编码/名称时触发 one_of HITL。"""
        result = preflight_tool("query_device_variables", {})
        assert result.interrupt is not None
        assert result.interrupt["tool"] == "query_device_variables"
        field_names = [field["name"] for field in result.interrupt["fields"]]
        assert field_names == ["device_code", "device_name"]

    @pytest.mark.parametrize(
        ("args", "expected"),
        [
            ({"device_code": "D001"}, "D001"),
            ({"device_name": "B口门禁"}, "B口门禁"),
        ],
    )
    def test_query_device_variables_accepts_each_one_of_group(self, args, expected):
        result = preflight_tool("query_device_variables", args)
        assert result.interrupt is None
        assert expected in result.args.values()

    def test_send_device_cmd_missing_device_triggers_resolver_hitl(self):
        result = preflight_tool("send_device_cmd", {"action": "播报"})
        assert result.interrupt is not None
        assert result.interrupt["type"] == "ask_params"
        assert result.interrupt["tool"] == "send_device_cmd"
        field_names = [f.get("name") for f in result.interrupt["fields"]]
        assert "device_code" in field_names

    def test_send_device_cmd_complete_args_skips_interrupt(self):
        with patch("contracts.device_command_resolver.resolve_device_command") as mock_resolve:
            mock_resolution = mock_resolve.return_value
            mock_resolution.is_complete.return_value = True
            mock_resolution.interrupt = None
            mock_resolution.to_tool_args.return_value = {
                "device_code": "D1",
                "variable_name": "play",
                "variable_value": "测试",
                "action": "播报",
            }
            result = preflight_tool(
                "send_device_cmd",
                {
                    "device_code": "D1",
                    "action": "播报",
                    "variable_value": "测试",
                },
            )
        assert result.interrupt is None
        assert result.args.get("device_code") == "D1"

    def test_hitl_fields_from_catalog(self):
        from contracts.tool_catalog_loader import get_hitl_fields

        fields = get_hitl_fields("query_alarms")
        assert fields
        assert fields[0]["type"] == "datetime_range"

    @patch("contracts.tool_preflight.settings")
    def test_disabled(self, mock_settings):
        mock_settings.agent_preflight_enabled = False
        result = preflight_tool("query_alarms", {})
        assert result.interrupt is None


class TestEnsureToolArgsOutsideGraph:
    def test_raises_mcp_hitl_for_missing_time(self):
        from contracts.hitl import McpHitlSignal

        with pytest.raises(McpHitlSignal):
            ensure_tool_args("query_alarms", {"start_time": "", "end_time": ""})

    def test_empty_optional_filters_omitted_from_current(self):
        """缺时间 HITL 时，空的 status/类型/级别不得预填成空白多选项。"""
        from contracts.hitl import McpHitlSignal

        with pytest.raises(McpHitlSignal) as exc_info:
            ensure_tool_args(
                "query_alarms",
                {
                    "start_time": "",
                    "end_time": "",
                    "device_name": "岗亭-1",
                    "status": "",
                    "alarm_category_id": "",
                    "alarm_rank_id": [""],
                    "device_code": "",
                },
            )
        current = exc_info.value.payload.get("current") or {}
        assert current.get("device_name") == "岗亭-1"
        assert "status" not in current
        assert "alarm_category_id" not in current
        assert "alarm_rank_id" not in current
        assert "device_code" not in current
        assert "start_time" not in current
        assert "end_time" not in current
