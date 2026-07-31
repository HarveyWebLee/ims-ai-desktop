"""用户原话时间抽取与 preflight 回填单测"""

from __future__ import annotations

from platform_mcp.runtime.time_range import (
    enrich_alarm_time_args,
    extract_alarm_time_range_from_message,
    extract_time_phrase,
)
from platform_mcp.runtime.tool_preflight import preflight_tool

from app.services.plan_confirm import infer_plan_params


class TestExtractAlarmTimeRangeFromMessage:
    def test_named_start_end_api_style(self):
        msg = (
            '查询 endTime"2026-07-02 11:17:00" startTime: "2026-07-02 11:00:00" '
            "这段时间范围内的告警并导出"
        )
        start, end = extract_alarm_time_range_from_message(msg)
        assert start == "2026-07-02 11:00:00"
        assert end == "2026-07-02 11:17:00"

    def test_snake_case_named_times(self):
        start, end = extract_alarm_time_range_from_message(
            'start_time="2026-01-01 00:00:00" end_time="2026-01-31 23:59:59" 查告警'
        )
        assert start == "2026-01-01 00:00:00"
        assert end == "2026-01-31 23:59:59"

    def test_two_datetimes_in_order(self):
        start, end = extract_alarm_time_range_from_message(
            "查 2026-07-02 11:00:00 到 2026-07-02 11:17:00 的告警"
        )
        assert start == "2026-07-02 11:00:00"
        assert end == "2026-07-02 11:17:00"

    def test_relative_phrase_only(self):
        start, end = extract_alarm_time_range_from_message("查近三天告警然后导出")
        assert start == "近三天"
        assert end == ""

    def test_yesterday_hour_range(self):
        start, end = extract_alarm_time_range_from_message(
            "查询昨天8点到9点的未处理告警数据并导出，然后批量处理",
        )
        assert "08:00" in start
        assert "09:00" in end
        assert start != end

    def test_yesterday_hour_range_with_minutes(self):
        start, end = extract_alarm_time_range_from_message(
            "查询昨天8点到8点10分的未处理告警数据并导出，然后批量处理",
        )
        assert "08:00" in start
        assert "08:10" in end

    def test_infer_plan_params_yesterday_hour_range(self):
        steps = [
            {"id": "1", "label": "查询", "tool": "query_alarms", "status": "pending"},
            {"id": "2", "label": "导出", "tool": "download_file", "status": "pending"},
        ]
        msg = "查询昨天8点到8点10分的未处理告警并导出"
        params = infer_plan_params(msg, steps)
        assert "08:00" in params["query_alarms"]["start_time"]
        assert "08:10" in params["query_alarms"]["end_time"]
        assert params["download_file"]["start_time"] == params["query_alarms"]["start_time"]
        assert params["download_file"]["end_time"] == params["query_alarms"]["end_time"]

    def test_extract_time_phrase_compat(self):
        assert extract_time_phrase("查近三天告警") == "近三天"


class TestInferPlanParamsAbsoluteTime:
    def test_query_export_with_absolute_range(self):
        steps = [
            {"id": "1", "label": "查询", "tool": "query_alarms", "status": "pending"},
            {"id": "2", "label": "导出", "tool": "download_file", "status": "pending"},
        ]
        msg = 'startTime: "2026-07-02 11:00:00" endTime: "2026-07-02 11:17:00" 查询告警并导出'
        params = infer_plan_params(msg, steps)
        assert params["query_alarms"]["start_time"] == "2026-07-02 11:00:00"
        assert params["query_alarms"]["end_time"] == "2026-07-02 11:17:00"
        assert params["download_file"]["start_time"] == "2026-07-02 11:00:00"
        assert params["download_file"]["end_time"] == "2026-07-02 11:17:00"


class TestPreflightEnrichFromUserMessage:
    def test_preflight_fills_empty_args_from_session_message(self):
        from platform_mcp.runtime.context import current_thread_id

        from app.services.session_store import session_store

        tid = "thread-enrich-test"
        token = current_thread_id.set(tid)
        try:
            session_store.append_user_message(
                tid,
                'startTime: "2026-07-02 11:00:00" endTime: "2026-07-02 11:17:00" 查告警',
            )
            result = preflight_tool(
                "query_alarms",
                {"start_time": "", "end_time": ""},
            )
        finally:
            current_thread_id.reset(token)

        assert result.interrupt is None
        assert result.args["start_time"] == "2026-07-02 11:00:00"
        assert result.args["end_time"] == "2026-07-02 11:17:00"

    def test_enrich_alarm_time_args_explicit_message(self):
        enriched = enrich_alarm_time_args(
            {"start_time": "", "end_time": ""},
            user_message='startTime: "2026-07-02 11:00:00" endTime: "2026-07-02 11:17:00"',
        )
        assert enriched["start_time"] == "2026-07-02 11:00:00"
        assert enriched["end_time"] == "2026-07-02 11:17:00"
