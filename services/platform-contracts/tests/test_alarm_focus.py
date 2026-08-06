"""告警焦点构造单测（空槽回填已交由大模型，不再经 enrich）。"""

from __future__ import annotations

from contracts.alarm_focus import (
    AlarmFocus,
    alarm_focus_from_tool_result,
)
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


class TestEnrichNoLongerAppliesAlarmFocus:
    def test_enrich_does_not_fill_from_focus(self):
        """即便存在 AlarmFocus，enrich 也不再静默写入工具参数。"""
        focus = AlarmFocus(
            start_time="2026-08-01 00:00:00",
            end_time="2026-08-04 23:59:59",
            status="1",
            alarm_id="ALM-1",
            total=1,
            source_tool="query_alarms",
        )
        assert focus.start_time
        args = enrich_tool_args_from_conversation(
            "download_file",
            {"resource": "alarm_report", "start_time": "", "end_time": ""},
            turn=TurnContext(utterance="导出一下", recent=()),
        )
        assert args == {"resource": "alarm_report", "start_time": "", "end_time": ""}

        detail = enrich_tool_args_from_conversation(
            "get_alarm_detail",
            {"alarm_id": ""},
            turn=TurnContext(utterance="打开这条详情", recent=()),
        )
        assert detail == {"alarm_id": ""}
