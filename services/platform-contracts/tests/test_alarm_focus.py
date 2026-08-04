"""告警焦点与会话空槽回填单测。"""

from __future__ import annotations

from contracts.alarm_focus import (
    AlarmFocus,
    alarm_focus_from_tool_result,
)
from contracts.context import current_alarm_focus
from contracts.conversation_context import (
    TurnContext,
    enrich_tool_args_from_conversation,
)


class TestAlarmFocusFromToolResult:
    def test_query_alarms_keeps_filters(self):
        focus = alarm_focus_from_tool_result(
            tool_name="query_alarms",
            payload={
                "ok": True,
                "data": {
                    "total": 88,
                    "items": [{"id": "a1"}, {"id": "a2"}],
                    "queryContext": {
                        "startTime": "2026-08-01 00:00:00",
                        "endTime": "2026-08-04 23:59:59",
                        "status": ["1"],
                        "deviceCodes": [],
                        "listApi": "getAlarmList",
                    },
                },
            },
        )
        assert focus is not None
        assert focus.start_time.startswith("2026-08-01")
        assert focus.status == "1"
        assert not focus.alarm_id
        assert focus.total == 88

    def test_query_alarms_unique_fills_id(self):
        focus = alarm_focus_from_tool_result(
            tool_name="query_alarms",
            payload={
                "ok": True,
                "data": {
                    "total": 1,
                    "items": [{"id": "ALM-9", "deviceCode": "D1"}],
                    "queryContext": {
                        "startTime": "2026-08-01 00:00:00",
                        "endTime": "2026-08-04 23:59:59",
                        "status": [],
                        "listApi": "getAlarmUnprocessList",
                    },
                },
            },
        )
        assert focus is not None
        assert focus.is_unique_alarm
        assert focus.alarm_id == "ALM-9"
        assert focus.status == "unprocessed"

    def test_get_alarm_detail(self):
        focus = alarm_focus_from_tool_result(
            tool_name="get_alarm_detail",
            payload={
                "ok": True,
                "data": {"id": "X1", "deviceName": "东门"},
            },
        )
        assert focus is not None
        assert focus.alarm_id == "X1"
        assert focus.is_unique_alarm


class TestEnrichUsesAlarmFocus:
    def test_download_fills_time_from_focus_when_user_text_has_none(self):
        focus = AlarmFocus(
            start_time="2026-08-01 00:00:00",
            end_time="2026-08-04 23:59:59",
            status="1",
            total=88,
            source_tool="query_alarms",
        )
        token = current_alarm_focus.set(focus)
        try:
            args = enrich_tool_args_from_conversation(
                "download_file",
                {"resource": "alarm_report", "start_time": "", "end_time": ""},
                turn=TurnContext(utterance="导出一下", recent=()),
            )
            assert args["start_time"] == "2026-08-01 00:00:00"
            assert args["end_time"] == "2026-08-04 23:59:59"
            assert args["status"] == "1"
        finally:
            current_alarm_focus.reset(token)

    def test_detail_fills_unique_alarm_id(self):
        focus = AlarmFocus(alarm_id="ALM-1", total=1, source_tool="query_alarms")
        token = current_alarm_focus.set(focus)
        try:
            args = enrich_tool_args_from_conversation(
                "get_alarm_detail",
                {"alarm_id": ""},
                turn=TurnContext(utterance="打开这条详情", recent=()),
            )
            assert args["alarm_id"] == "ALM-1"
        finally:
            current_alarm_focus.reset(token)

    def test_batch_unique_fills_alarm_ids(self):
        focus = AlarmFocus(alarm_id="ALM-1", total=1, source_tool="query_alarms")
        token = current_alarm_focus.set(focus)
        try:
            args = enrich_tool_args_from_conversation(
                "batch_confirm_alarms",
                {"alarm_ids": "", "start_time": "", "end_time": ""},
                turn=TurnContext(utterance="确认这条", recent=()),
            )
            assert args["alarm_ids"] == "ALM-1"
        finally:
            current_alarm_focus.reset(token)

    def test_does_not_overwrite_explicit_time(self):
        focus = AlarmFocus(
            start_time="2026-08-01 00:00:00",
            end_time="2026-08-04 23:59:59",
            source_tool="query_alarms",
        )
        token = current_alarm_focus.set(focus)
        try:
            args = enrich_tool_args_from_conversation(
                "query_alarms",
                {"start_time": "近七天", "end_time": ""},
                turn=TurnContext(utterance="再查一遍", recent=()),
            )
            assert args["start_time"] == "近七天"
        finally:
            current_alarm_focus.reset(token)
