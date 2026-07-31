"""告警时间解析与 HITL 缺参策略单测"""

from __future__ import annotations

from platform_mcp.runtime.time_range import resolve_alarm_time_range
from platform_mcp.runtime.tools.alarm import _resolve_or_prepare_alarm_times


class TestResolveOrPrepareAlarmTimes:
    def test_empty_time_requires_hitl(self):
        """未提供时间范围时必须走 HITL，禁止默认近 7 天"""
        start, end, needs_hitl = _resolve_or_prepare_alarm_times("", "")
        assert needs_hitl is True
        assert start == ""
        assert end == ""

    def test_relative_time_parsed(self):
        start, end, needs_hitl = _resolve_or_prepare_alarm_times("近三天", "")
        assert needs_hitl is False
        assert start
        assert end

    def test_half_year_relative_time_parsed(self):
        """「近半年」应解析为约 6 个自然月，而非近一个月"""
        resolved = resolve_alarm_time_range("近半年", "")
        assert resolved is not None
        start, end, needs_hitl = _resolve_or_prepare_alarm_times("近半年", "")
        assert needs_hitl is False
        assert start == resolved[0]
        assert end == resolved[1]
        # 起始日约为当前日往前 6 个自然月（按东八区日历）
        assert start[:10] < end[:10]

    def test_unparseable_time_requires_hitl(self):
        start, end, needs_hitl = _resolve_or_prepare_alarm_times("abc123", "")
        assert needs_hitl is True
        assert start == "abc123"
        assert end == ""

    def test_absolute_datetime_range_parsed(self):
        """HITL 日期选择器提交的绝对时间应可解析"""
        start = "2026-07-01 00:00:00"
        end = "2026-07-02 23:59:59"
        resolved = resolve_alarm_time_range(start, end)
        assert resolved is not None
        assert resolved[0] == start
        assert resolved[1] == end

        _, _, needs_hitl = _resolve_or_prepare_alarm_times(start, end)
        assert needs_hitl is False
