"""告警导出批次规划与 URL 构建单测；岗哨交接导出分发单测"""

from __future__ import annotations

import json
from unittest.mock import patch

from contracts.export_infer import (
    EXPORT_ALARM_BATCH_MAX,
    infer_download_resource,
)
from platform_mcp.runtime.tools.export import (
    _build_app_download_url,
    _build_export_download_actions,
    execute_acs_record_export,
    execute_duty_info_export,
    execute_duty_manage_export,
    execute_sentry_handover_export,
    plan_alarm_export_batches,
)


class TestPlanAlarmExportBatches:
    def test_small_total_single_batch(self):
        assert plan_alarm_export_batches(60) == [(1, 60)]

    def test_exact_batch_max(self):
        assert plan_alarm_export_batches(EXPORT_ALARM_BATCH_MAX) == [(1, EXPORT_ALARM_BATCH_MAX)]

    def test_over_batch_max_multiple_files(self):
        assert plan_alarm_export_batches(65000) == [
            (1, EXPORT_ALARM_BATCH_MAX),
            (2, EXPORT_ALARM_BATCH_MAX),
            (3, 5000),
        ]

    def test_zero_total(self):
        assert plan_alarm_export_batches(0) == []


class TestExportAlarmUrl:
    def test_build_url_includes_dynamic_page_and_size(self):
        url = _build_app_download_url(
            "/alarm/exportAlarm",
            {
                "page": 2,
                "size": 5000,
                "startTime": "2026-01-02 00:00:00",
                "endTime": "2026-07-02 23:59:59",
            },
        )
        assert "page=2" in url
        assert "size=5000" in url

    def test_build_multi_download_actions(self):
        base = {
            "startTime": "2026-01-02 00:00:00",
            "endTime": "2026-07-02 23:59:59",
            "deviceCodes": [],
            "variableNames": [],
            "alarmCategoryId": [],
            "alarmRankId": [],
            "status": [],
        }
        actions = _build_export_download_actions(
            base_params=base,
            batches=[(1, 60)],
            start_fmt=base["startTime"],
            end_fmt=base["endTime"],
        )
        assert len(actions) == 1
        assert actions[0]["action"] == "download"
        assert "size=60" in actions[0]["url"]

        multi = _build_export_download_actions(
            base_params=base,
            batches=[(1, EXPORT_ALARM_BATCH_MAX), (2, 5000)],
            start_fmt=base["startTime"],
            end_fmt=base["endTime"],
        )
        assert len(multi) == 2
        assert "第1批共2" in multi[0]["filename"]
        assert "size=5000" in multi[1]["url"]


class TestSentryHandoverExport:
    def test_infer_resource(self):
        assert infer_download_resource("导出近三天岗哨交接") == "sentry_handover"
        assert infer_download_resource("导出近三天值班信息") == "duty_info"
        assert infer_download_resource("导出近三天值班管理") == "duty_manage"
        assert infer_download_resource("导出近七天出入信息") == "acs_record"
        assert infer_download_resource("导出门禁通行记录") == "acs_record"
        assert infer_download_resource("导出告警") == "alarm_report"

    def test_execute_builds_duty_download_url(self):
        with (
            patch(
                "platform_mcp.runtime.tools.export._count_platform_list_total",
                return_value=12,
            ),
            patch("platform_mcp.runtime.tools.export.ask_user_confirm", return_value=True),
        ):
            raw = execute_sentry_handover_export(
                start_time="2026-07-01 00:00:00",
                end_time="2026-07-20 23:59:59",
                require_confirm=True,
            )
        result = json.loads(raw)
        assert result["ok"] is True
        assert result["data"]["resource"] == "sentry_handover"
        action = result["client_action"]
        assert action["action"] == "download"
        assert "/duty/exportSentryHandover" in action["url"]
        assert "startTime=" in action["url"]
        assert "岗哨交接" in action["filename"]

    def test_execute_user_cancelled(self):
        with (
            patch(
                "platform_mcp.runtime.tools.export._count_platform_list_total",
                return_value=3,
            ),
            patch("platform_mcp.runtime.tools.export.ask_user_confirm", return_value=False),
        ):
            raw = execute_sentry_handover_export(
                start_time="近三天",
                end_time="",
                require_confirm=True,
            )
        result = json.loads(raw)
        assert result["ok"] is False
        assert result.get("user_cancelled") is True


class TestDutyInfoExport:
    def test_execute_builds_duty_info_download_url(self):
        with (
            patch(
                "platform_mcp.runtime.tools.export._count_platform_list_total",
                return_value=8,
            ),
            patch("platform_mcp.runtime.tools.export.ask_user_confirm", return_value=True),
        ):
            raw = execute_duty_info_export(
                start_time="2026-07-01 00:00:00",
                end_time="2026-07-20 23:59:59",
                require_confirm=True,
            )
        result = json.loads(raw)
        assert result["ok"] is True
        assert result["data"]["resource"] == "duty_info"
        action = result["client_action"]
        assert "/duty/exportDutyInfo" in action["url"]
        assert "值班信息" in action["filename"]


class TestDutyManageExport:
    def test_execute_builds_duty_manage_download_url(self):
        with (
            patch(
                "platform_mcp.runtime.tools.export._count_platform_list_total",
                return_value=5,
            ),
            patch("platform_mcp.runtime.tools.export.ask_user_confirm", return_value=True),
        ):
            raw = execute_duty_manage_export(
                start_time="2026-07-01 00:00:00",
                end_time="2026-07-20 23:59:59",
                require_confirm=True,
            )
        result = json.loads(raw)
        assert result["ok"] is True
        assert result["data"]["resource"] == "duty_manage"
        assert "/duty/exportDutyManage" in result["client_action"]["url"]
        assert "值班管理" in result["client_action"]["filename"]


class TestAcsRecordExport:
    def test_execute_builds_acs_record_download_url(self):
        with (
            patch(
                "platform_mcp.runtime.tools.export._count_platform_list_total",
                return_value=20,
            ),
            patch("platform_mcp.runtime.tools.export.ask_user_confirm", return_value=True),
        ):
            raw = execute_acs_record_export(
                start_time="2026-07-01 00:00:00",
                end_time="2026-07-20 23:59:59",
                person_id="p-001",
                require_confirm=True,
            )
        result = json.loads(raw)
        assert result["ok"] is True
        assert result["data"]["resource"] == "acs_record"
        url = result["client_action"]["url"]
        assert "/acs/exportAcsRecord" in url
        assert "personId=p-001" in url
        assert "出入信息" in result["client_action"]["filename"]
