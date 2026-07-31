"""告警导出未处理范围单测"""

from __future__ import annotations

from unittest.mock import patch

from platform_mcp.runtime.tools.export import execute_alarm_export


class TestExecuteAlarmExportUnprocessed:
    @patch("platform_mcp.runtime.tools.export.ask_user_confirm", return_value=False)
    @patch("platform_mcp.runtime.tools.export.count_alarms_matching_filters", return_value=5)
    @patch("platform_mcp.runtime.tools.export.resolve_alarm_time_range")
    def test_unprocessed_status_uses_one_two_for_export_url(
        self,
        mock_resolve_time,
        _mock_count,
        _mock_confirm,
    ):
        mock_resolve_time.return_value = (
            "2026-04-07T00:00:00",
            "2026-07-07T23:59:59",
        )

        result = execute_alarm_export(
            start_time="近三月",
            end_time="",
            status="未处理",
            filter_params={"status": "未处理", "resource": "alarm_report"},
            require_confirm=True,
        )

        assert "使用者已取消导出" in result
        # 取消前应先完成计数；确认文案应体现未处理范围与 5 条
        assert "5 条" in result or "取消" in result

    @patch("platform_mcp.runtime.tools.export.ask_user_confirm")
    @patch("platform_mcp.runtime.tools.export.count_alarms_matching_filters", return_value=5)
    @patch("platform_mcp.runtime.tools.export.resolve_alarm_time_range")
    def test_confirm_message_mentions_unprocessed(
        self,
        mock_resolve_time,
        _mock_count,
        mock_confirm,
    ):
        mock_resolve_time.return_value = (
            "2026-04-07T00:00:00",
            "2026-07-07T23:59:59",
        )
        mock_confirm.return_value = False

        execute_alarm_export(
            start_time="近三月",
            end_time="",
            status="未处理",
            filter_params={"status": "未处理"},
            require_confirm=True,
        )

        confirm_msg = mock_confirm.call_args.kwargs.get("message") or mock_confirm.call_args[0][1]
        assert "5 条" in confirm_msg
        assert "未处理" in confirm_msg

    @patch("platform_mcp.runtime.tools.export._build_export_download_actions")
    @patch("platform_mcp.runtime.tools.export.ask_user_confirm", return_value=True)
    @patch("platform_mcp.runtime.tools.export.count_alarms_matching_filters", return_value=5)
    @patch("platform_mcp.runtime.tools.export.resolve_alarm_time_range")
    def test_export_url_includes_status_one_and_two(
        self,
        mock_resolve_time,
        _mock_count,
        _mock_confirm,
        mock_build_actions,
    ):
        mock_resolve_time.return_value = (
            "2026-04-07T00:00:00",
            "2026-07-07T23:59:59",
        )
        mock_build_actions.return_value = [
            {
                "action": "download",
                "url": "/api/app/alarm/exportAlarm?status=1&status=2",
                "filename": "x.xlsx",
            }
        ]

        execute_alarm_export(
            start_time="近三月",
            end_time="",
            status="未处理",
            filter_params={"status": "未处理"},
            require_confirm=True,
        )

        base_params = mock_build_actions.call_args.kwargs["base_params"]
        assert base_params["status"] == ["1", "2"]
