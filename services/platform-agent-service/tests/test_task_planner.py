"""规则任务规划 build_task_plan 单测"""

from __future__ import annotations

from app.services.task_planner import (
    build_replan_after_failure,
    build_task_plan,
    download_export_step_label,
    extract_alarm_status_from_message,
)


class TestExtractAlarmStatus:
    def test_unprocessed(self):
        assert extract_alarm_status_from_message("查询并导出近三月的未处理的告警数据") == "未处理"

    def test_no_status(self):
        assert extract_alarm_status_from_message("查询并导出近三月的告警数据") == ""


class TestBuildTaskPlan:
    def test_query_and_export_implicit_compound_no_duplicate(self):
        """「查询并导出」：连接词切分仅得 1 步时应走隐式复合，不得重复导出。"""
        plan = build_task_plan("查询并导出近三月的告警数据")
        assert plan is not None
        assert len(plan) == 2
        assert [s["tool"] for s in plan] == ["query_alarms", "download_file"]
        assert plan[0]["label"] == "查询告警数据"
        assert plan[1]["label"] == "导出告警报表"

    def test_query_and_export_with_unprocessed_labels(self):
        plan = build_task_plan("查询并导出近三月的未处理的告警数据")
        assert plan is not None
        assert len(plan) == 2
        assert plan[0]["label"] == "查询未处理告警"
        assert plan[1]["label"] == "导出未处理告警报表"

    def test_explicit_compound_then_still_works(self):
        """显式「然后」连接的多步计划保持正确顺序。"""
        plan = build_task_plan("查近三天告警然后导出")
        assert plan is not None
        assert len(plan) == 2
        assert [s["tool"] for s in plan] == ["query_alarms", "download_file"]

    def test_query_export_then_batch_process_three_steps(self):
        """「查询…并导出，然后批量处理」应生成三步 Plan。"""
        msg = "查询昨天8点到9点的未处理告警数据并导出，然后批量处理"
        plan = build_task_plan(msg)
        assert plan is not None
        assert len(plan) == 3
        assert [s["tool"] for s in plan] == [
            "query_alarms",
            "download_file",
            "batch_process_alarms",
        ]
        assert plan[0]["label"] == "查询未处理告警"
        assert plan[1]["label"] == "导出未处理告警报表"
        assert plan[2]["label"] == "批量处理告警"

    def test_batch_process_clause_only_in_second_part(self):
        """第二子句仅「批量处理」时须识别 batch_process_alarms。"""
        plan = build_task_plan("查近三天告警然后批量处理")
        assert plan is not None
        assert [s["tool"] for s in plan] == ["query_alarms", "batch_process_alarms"]

    def test_navigate_with_pause_splits_into_two_steps(self):
        """导航子句含停留指令时拆为 navigate + pause。"""
        plan = build_task_plan("先跳转到设施管理，停留10s，然后打开设备变量，最后导出近三月告警")
        assert plan is not None
        assert [s["tool"] for s in plan] == [
            "navigate_to",
            "pause",
            "navigate_to",
            "download_file",
        ]
        assert plan[0]["label"] == "跳转到设施管理"
        assert plan[1]["label"] == "停留 10 秒"
        assert plan[1]["params"] == {"seconds": 10}


class TestDownloadExportStepLabel:
    def test_duty_manage_label(self):
        assert download_export_step_label("导出近三天值班管理") == "导出值班管理"

    def test_retry_duty_manage_label(self):
        assert download_export_step_label("导出近三天值班管理", retry=True) == "重试导出值班管理"

    def test_acs_record_from_args(self):
        assert (
            download_export_step_label(
                "导出",
                resource="acs_record",
                retry=True,
            )
            == "重试导出出入信息"
        )


class TestBuildReplanAfterFailure:
    def test_download_file_retry_uses_resource_from_args(self):
        original = [
            {
                "id": "1",
                "label": "导出值班管理",
                "tool": "download_file",
                "status": "error",
            }
        ]
        steps, reason = build_replan_after_failure(
            original_steps=original,
            failed_tool="download_file",
            error_summary="502",
            user_message="导出近三天值班管理",
            failed_args={"resource": "duty_manage", "start_time": "近三天"},
        )
        assert steps[-1]["label"] == "重试导出值班管理"
        assert "重试导出值班管理" in reason

    def test_query_fail_recovery_export_non_alarm(self):
        original = [
            {"id": "1", "label": "查询告警", "tool": "query_alarms", "status": "error"},
            {
                "id": "2",
                "label": "导出岗哨交接记录",
                "tool": "download_file",
                "status": "skipped",
            },
        ]
        steps, _ = build_replan_after_failure(
            original_steps=original,
            failed_tool="query_alarms",
            error_summary="timeout",
            user_message="导出近三天岗哨交接",
        )
        export_steps = [
            s for s in steps if s.get("tool") == "download_file" and s["status"] == "pending"
        ]
        assert len(export_steps) == 1
        assert export_steps[0]["label"] == "导出岗哨交接记录"
