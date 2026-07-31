"""告警按设备 / 状态筛选传参单测（对齐 getAlarmList / getAlarmUnprocessList）。"""

from __future__ import annotations

from unittest.mock import patch

from platform_mcp.runtime.tools.alarm import (
    _ALARM_API_LIST,
    _ALARM_API_UNPROCESSED,
    _apply_alarm_filter_fields,
    _parse_alarm_list_scope,
    build_alarm_list_filter_payload,
    resolve_alarm_device_filter,
)


class TestParseAlarmListScope:
    def test_unprocessed_uses_unprocess_api(self):
        api, codes = _parse_alarm_list_scope("未处理")
        assert api == _ALARM_API_UNPROCESSED
        assert codes == []

    def test_unconfirmed_maps_to_status_1(self):
        api, codes = _parse_alarm_list_scope("未确认")
        assert api == _ALARM_API_LIST
        assert codes == ["1"]

    def test_pending_confirm_alias(self):
        api, codes = _parse_alarm_list_scope("待确认")
        assert api == _ALARM_API_LIST
        assert codes == ["1"]


class TestApplyDeviceCodes:
    def test_device_code_writes_device_codes(self):
        payload: dict = {
            "deviceCodes": [],
            "variableNames": [],
            "alarmCategoryId": [],
            "alarmRankId": [],
            "status": [],
        }
        _apply_alarm_filter_fields(payload, {"device_code": "zhonglian_103"})
        assert payload["deviceCodes"] == ["zhonglian_103"]

    def test_build_list_payload_includes_device_codes(self):
        payload = build_alarm_list_filter_payload(
            start_time="2026-07-01 00:00:00",
            end_time="2026-07-02 23:59:59",
            filter_params={"device_code": "D001"},
        )
        assert payload["deviceCodes"] == ["D001"]


class TestResolveAlarmDeviceFilter:
    @patch("platform_mcp.runtime.tools.device._resolve_device_code")
    def test_resolve_by_name(self, mock_resolve):
        mock_resolve.return_value = ("D001", {"deviceCode": "D001"}, None)
        params: dict = {"device_name": "一号泵"}
        codes, err = resolve_alarm_device_filter(
            params,
            device_name="一号泵",
            hitl_tool="query_alarms",
        )
        assert err is None
        assert codes == ["D001"]
        assert params["device_code"] == "D001"
        mock_resolve.assert_called_once()
        assert mock_resolve.call_args.kwargs.get("hitl_tool") == "query_alarms"

    def test_empty_device_ok(self):
        params: dict = {}
        codes, err = resolve_alarm_device_filter(params)
        assert err is None
        assert codes == []
