"""告警状态语义与列表 API 路由"""

from __future__ import annotations

from unittest.mock import patch

from platform_mcp.runtime.tools.alarm import (
    _ALARM_API_LIST,
    _ALARM_API_UNPROCESSED,
    _build_confirm_message,
    _is_pending_confirm_record,
    _map_alarm_status_token,
    _normalize_hitl_status_list,
    _parse_alarm_list_scope,
    _parse_hitl_status_scope,
    _prepare_confirm_records,
    _resolve_platform_alarm_times,
    build_alarm_list_filter_payload,
    build_alarm_unprocess_list_payload,
    export_status_codes_for_scope,
    resolve_alarm_filter_scope,
)

from app.middleware.auth import decode_jwt_payload, get_username_from_token


class TestAlarmListScope:
    def test_unprocessed_uses_unprocess_api(self):
        api, codes = _parse_alarm_list_scope("未处理")
        assert api == _ALARM_API_UNPROCESSED
        assert codes == []

    def test_unconfirmed_uses_alarm_list_status_one(self):
        api, codes = _parse_alarm_list_scope("未确认")
        assert api == _ALARM_API_LIST
        assert codes == ["1"]

    def test_pending_confirm(self):
        api, codes = _parse_alarm_list_scope("待确认")
        assert api == _ALARM_API_LIST
        assert codes == ["1"]

    def test_hitl_unprocessed_scope(self):
        api, codes = _parse_hitl_status_scope("unprocessed")
        assert api == _ALARM_API_UNPROCESSED
        assert codes == []


class TestMapAlarmStatusToken:
    def test_unconfirmed_is_one(self):
        assert _map_alarm_status_token("未确认") == "1"

    def test_unprocessed_not_a_status_code(self):
        assert _map_alarm_status_token("未处理") == ""

    def test_normalize_strips_unprocessed(self):
        assert _normalize_hitl_status_list("unprocessed") == []
        assert _normalize_hitl_status_list(["unprocessed", "1"]) == ["1"]


class TestAlarmFilterScope:
    def test_resolve_unprocessed_from_string_status(self):
        api, codes = resolve_alarm_filter_scope({"status": "未处理"})
        assert api == _ALARM_API_UNPROCESSED
        assert codes == []

    def test_export_status_full_unprocessed(self):
        assert export_status_codes_for_scope(_ALARM_API_UNPROCESSED, []) == ["1", "2"]

    def test_export_status_pending_within_unprocessed(self):
        assert export_status_codes_for_scope(_ALARM_API_UNPROCESSED, ["1"]) == ["1"]


class TestResolvePlatformAlarmTimes:
    def test_relative_three_days(self):
        start, end = _resolve_platform_alarm_times("近三天", "")
        assert start.startswith("2026-")
        assert " " in start
        assert "T" not in start


class TestAlarmListPayload:
    def test_get_alarm_list_not_raw_relative(self):
        start_iso, end_iso = _resolve_platform_alarm_times("近三天", "")
        payload = build_alarm_list_filter_payload(
            start_time=start_iso,
            end_time=end_iso,
            filter_params={"status": ["1"]},
            status_fallback="1",
        )
        assert payload["startTime"] != "近三天"
        assert payload["status"] == ["1"]

    def test_unprocess_payload_shape(self):
        start, end = _resolve_platform_alarm_times("近三天", "")
        payload = build_alarm_unprocess_list_payload(
            start_time=start,
            end_time=end,
            filter_params={"alarm_category_id": ["10"]},
            status_codes=[],
        )
        assert payload["alarmCategoryId"] == ["10"]
        assert payload["status"] == []


class TestPendingConfirmFilter:
    def test_status_one(self):
        assert _is_pending_confirm_record({"status": 1}) is True

    def test_status_two(self):
        assert _is_pending_confirm_record({"status": 2}) is False


class TestConfirmMessage:
    def test_unprocessed_scope_hint(self):
        msg = _build_confirm_message(
            [{"id": 1, "status": 1}],
            raw_records=[{"id": 1, "status": 1}, {"id": 2, "status": 2}],
            list_api=_ALARM_API_UNPROCESSED,
        )
        assert "未处理 2 条" in msg
        assert "待确认 1 条" in msg
        assert "已确认" in msg


class TestBatchWriteEmptyMessage:
    def test_suggest_process_when_only_confirmed(self):
        from platform_mcp.runtime.tools.alarm import _build_batch_write_empty_message

        msg = _build_batch_write_empty_message(
            operation="确认",
            source_label="待确认",
            target_label="已确认",
            raw_records=[{"id": 1, "status": 2}],
            alternate_hint="请使用批量处理。",
        )
        assert "已确认 1 条" in msg
        assert "待确认 0" not in msg
        assert "批量处理" in msg


class TestConfirmedRecord:
    def test_status_two(self):
        from platform_mcp.runtime.tools.alarm import _is_confirmed_record

        assert _is_confirmed_record({"status": 2}) is True
        assert _is_confirmed_record({"status": 1}) is False


class TestProcessEligibleRecord:
    def test_pending_and_confirmed(self):
        from platform_mcp.runtime.tools.alarm import _is_process_eligible_record

        assert _is_process_eligible_record({"status": 1}) is True
        assert _is_process_eligible_record({"status": 2}) is True
        assert _is_process_eligible_record({"status": 3}) is False


class TestResolveBatchWriteScope:
    def test_process_default_unprocessed(self):
        from platform_mcp.runtime.tools.alarm import (
            _ALARM_API_UNPROCESSED,
            _resolve_batch_write_fetch_scope,
        )

        api, codes = _resolve_batch_write_fetch_scope("", operation="process")
        assert api == _ALARM_API_UNPROCESSED
        assert codes == []


class TestPrepareConfirmRecords:
    def test_adds_confirm_person(self):
        record = {"id": "a1", "alarmCategoryId": 3, "status": 1}
        with patch(
            "platform_mcp.runtime.tools.alarm.get_username_from_token",
            return_value="root",
        ):
            prepared, err = _prepare_confirm_records([record])
        assert err is None
        assert prepared[0]["confirmPerson"] == "root"


class TestJwtUsername:
    def test_decode_empty(self):
        assert decode_jwt_payload("") == {}

    def test_get_username_none_without_token(self):
        assert get_username_from_token(None) is None
