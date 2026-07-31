"""catalog 加载与 preflight 映射单测"""

from __future__ import annotations

from contracts.tool_catalog_loader import (
    format_registered_tools_bindings,
    get_preflight_config,
    get_tool_platform_api,
    parse_platform_api_ref,
)
from contracts.tool_preflight import preflight_tool


class TestToolCatalogLoader:
    def test_parse_platform_api_ref(self):
        assert parse_platform_api_ref("POST /api/app/alarm/getAlarmList") == (
            "/alarm/getAlarmList",
            "POST",
        )
        assert parse_platform_api_ref("GET /api/app/alarm/exportAlarm") == (
            "/alarm/exportAlarm",
            "GET",
        )
        assert parse_platform_api_ref("") is None

    def test_get_tool_platform_api_from_catalog(self):
        parsed = get_tool_platform_api("query_alarms")
        assert parsed == ("/alarm/getAlarmList", "POST")

    def test_format_bindings_includes_all_tools(self):
        table = format_registered_tools_bindings()
        for name in (
            "navigate_to",
            "query_alarms",
            "batch_process_alarms",
        ):
            assert f"`{name}`" in table

    def test_get_preflight_config_from_catalog(self):
        cfg = get_preflight_config("query_alarms")
        assert cfg is not None
        assert cfg.get("alarm_time") is True
        assert get_preflight_config("navigate_to") is None
        assert get_preflight_config("unknown_tool_xyz") is None


class TestPreflightPlatformMapping:
    def test_get_alarm_detail_with_id_passes(self):
        result = preflight_tool("get_alarm_detail", {"alarm_id": "ALM-001"})
        assert result.interrupt is None

    def test_batch_confirm_with_alarm_ids_skips_time(self):
        result = preflight_tool(
            "batch_confirm_alarms",
            {"alarm_ids": "1,2,3", "start_time": "", "end_time": ""},
        )
        assert result.interrupt is None

    def test_batch_process_missing_scope(self):
        result = preflight_tool("batch_process_alarms", {})
        assert result.interrupt is not None
        assert result.interrupt["tool"] == "batch_process_alarms"
