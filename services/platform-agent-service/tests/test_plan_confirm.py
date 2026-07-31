"""Phase C2 plan_confirm 门控单测"""

from __future__ import annotations

from unittest.mock import patch

from platform_mcp.runtime.time_range import extract_time_phrase

from app.graph.context import assemble_context
from app.services.plan_confirm import (
    PLAN_CONFIRM_TOOL,
    infer_plan_params,
    nav_path_from_step_label,
    plan_needs_user_confirm,
    prepare_plan_confirm_gate,
    propagate_query_alarm_params_to_export,
    resolve_step_tool_params,
)
from app.services.session_store import (
    clear_thread_orchestration,
    get_thread_bpmn_snapshot,
    set_thread_bpmn_snapshot,
)


class TestPlanConfirmHelpers:
    def test_extract_time_phrase(self):
        assert extract_time_phrase("查近三天告警然后导出") == "近三天"

    def test_infer_plan_params_sentry_handover_export(self):
        steps = [
            {"id": "1", "label": "导出", "tool": "download_file", "status": "pending"},
        ]
        params = infer_plan_params("导出近三天岗哨交接记录", steps)
        assert params["download_file"]["resource"] == "sentry_handover"
        assert params["download_file"]["start_time"] == "近三天"
        assert "status" not in params["download_file"]

    def test_infer_plan_params_duty_info_export(self):
        steps = [
            {"id": "1", "label": "导出", "tool": "download_file", "status": "pending"},
        ]
        params = infer_plan_params("导出近一周值班信息", steps)
        assert params["download_file"]["resource"] == "duty_info"
        assert params["download_file"]["start_time"] == "近一周"
        assert "status" not in params["download_file"]

    def test_infer_plan_params_duty_manage_export(self):
        steps = [
            {"id": "1", "label": "导出", "tool": "download_file", "status": "pending"},
        ]
        params = infer_plan_params("导出近三天值班管理", steps)
        assert params["download_file"]["resource"] == "duty_manage"

    def test_infer_plan_params_acs_record_export(self):
        steps = [
            {"id": "1", "label": "导出", "tool": "download_file", "status": "pending"},
        ]
        params = infer_plan_params("导出近七天出入信息", steps)
        assert params["download_file"]["resource"] == "acs_record"

    def test_propagate_skips_non_alarm_export(self):
        """岗哨交接导出不应被 query_alarms 的 status 污染。"""
        steps = [
            {"id": "1", "label": "查询", "tool": "query_alarms", "status": "done"},
            {"id": "2", "label": "导出", "tool": "download_file", "status": "pending"},
        ]
        params_by_tool = {
            "query_alarms": {
                "start_time": "2025-01-01T00:00:00",
                "end_time": "2025-01-31T23:59:59",
                "status": ["1"],
            },
            "download_file": {
                "resource": "sentry_handover",
                "start_time": "近三天",
            },
        }
        propagate_query_alarm_params_to_export(params_by_tool, steps)
        assert params_by_tool["download_file"]["resource"] == "sentry_handover"
        assert "status" not in params_by_tool["download_file"]
        assert params_by_tool["download_file"]["start_time"] == "近三天"

    def test_infer_plan_params_query_export(self):
        steps = [
            {"id": "1", "label": "查询", "tool": "query_alarms", "status": "pending"},
            {"id": "2", "label": "导出", "tool": "download_file", "status": "pending"},
        ]
        params = infer_plan_params("查近三天告警然后导出", steps)
        assert params["query_alarms"]["start_time"] == "近三天"
        assert params["download_file"]["resource"] == "alarm_report"
        assert "status" not in params["query_alarms"]

    def test_infer_plan_params_extracts_unprocessed_status(self):
        steps = [
            {"id": "1", "label": "查询", "tool": "query_alarms", "status": "pending"},
            {"id": "2", "label": "导出", "tool": "download_file", "status": "pending"},
        ]
        msg = "查询并导出近三月的未处理的告警数据"
        params = infer_plan_params(msg, steps)
        assert params["query_alarms"]["status"] == "未处理"
        assert params["download_file"]["status"] == "未处理"

    def test_infer_plan_params_device_name_from_conditional_message(self):
        """设备槽位不由规则 infer；条件图应走 Flow IR.args。"""
        steps = [
            {
                "id": "step_query",
                "label": "查状态",
                "tool": "get_device_detail",
                "status": "pending",
            },
            {
                "id": "step_open",
                "label": "开门",
                "tool": "send_device_cmd",
                "status": "pending",
            },
        ]
        params = infer_plan_params("查716门禁，在线开门，离线查历史", steps)
        assert "get_device_detail" not in params
        assert "send_device_cmd" not in params

    def test_nav_path_from_step_label(self):
        assert nav_path_from_step_label("跳转到设施页面，") == "设施页面"
        assert nav_path_from_step_label("跳转到设备变量，") == "设备变量"

    def test_resolve_step_tool_params_multi_navigate(self):
        """连续 navigate_to 步骤应从各自 label 取 path，而非共用 params_by_tool。"""
        steps = [
            {"id": "1", "label": "跳转到设施页面，", "tool": "navigate_to"},
            {"id": "2", "label": "跳转到设备变量，", "tool": "navigate_to"},
        ]
        params_by_tool = {"navigate_to": {"path": "到设施页面"}}
        assert resolve_step_tool_params(steps[0], params_by_tool)["path"] == "设施页面"
        assert resolve_step_tool_params(steps[1], params_by_tool)["path"] == "设备变量"

    def test_propagate_query_params_to_export_after_hitl(self):
        """查询步 HITL 补参后，导出步应复用相同时间与筛选条件。"""
        steps = [
            {"id": "1", "label": "查询", "tool": "query_alarms", "status": "done"},
            {"id": "2", "label": "导出", "tool": "download_file", "status": "pending"},
        ]
        params_by_tool = {
            "query_alarms": {
                "start_time": "2025-01-01T00:00:00",
                "end_time": "2025-01-31T23:59:59",
                "status": ["1"],
                "alarm_category_id": ["cat-1"],
            },
            "download_file": {
                "resource": "alarm_report",
                "start_time": "",
                "end_time": "",
            },
        }
        propagate_query_alarm_params_to_export(params_by_tool, steps)
        export = params_by_tool["download_file"]
        assert export["start_time"] == "2025-01-01T00:00:00"
        assert export["end_time"] == "2025-01-31T23:59:59"
        assert export["status"] == ["1"]
        assert export["alarm_category_id"] == ["cat-1"]

    def test_propagate_skips_when_export_already_has_time(self):
        steps = [
            {"id": "1", "label": "查询", "tool": "query_alarms", "status": "done"},
            {"id": "2", "label": "导出", "tool": "download_file", "status": "pending"},
        ]
        params_by_tool = {
            "query_alarms": {
                "start_time": "2025-01-01T00:00:00",
                "end_time": "2025-01-31T23:59:59",
            },
            "download_file": {
                "resource": "alarm_report",
                "start_time": "近三天",
                "end_time": "",
            },
        }
        propagate_query_alarm_params_to_export(params_by_tool, steps)
        assert params_by_tool["download_file"]["start_time"] == "近三天"


class TestPlanNeedsUserConfirm:
    def test_write_plan_requires_confirm(self):
        steps = [
            {"tool": "query_alarms"},
            {"tool": "download_file"},
        ]
        assert plan_needs_user_confirm(steps) is True

    def test_read_only_plan_skips_when_write_only(self):
        steps = [
            {"tool": "navigate_to"},
            {"tool": "query_alarms"},
        ]
        assert plan_needs_user_confirm(steps) is False

    @patch("app.services.plan_confirm.settings")
    def test_read_only_still_confirms_when_write_only_off(self, mock_settings):
        mock_settings.agent_plan_confirm_write_only = False
        steps = [{"tool": "navigate_to"}, {"tool": "query_alarms"}]
        assert plan_needs_user_confirm(steps) is True


class TestPreparePlanConfirmGate:
    def test_multi_step_triggers_gate(self):
        ctx = assemble_context(
            thread_id="t1",
            message="查近三天告警然后导出",
            metadata={"current_path": "/home"},
        )
        gate = prepare_plan_confirm_gate(ctx)
        assert gate is not None
        assert len(gate.steps) >= 2
        assert gate.interrupt_payload["type"] == "plan_confirm"
        assert gate.interrupt_payload["tool"] == PLAN_CONFIRM_TOOL
        assert gate.interrupt_payload["steps"]
        assert all(s["status"] == "awaiting_confirm" for s in gate.steps)
        assert "graph" in gate.interrupt_payload
        assert len(gate.interrupt_payload["graph"]["nodes"]) >= 3

    def test_single_step_no_gate(self):
        ctx = assemble_context(
            thread_id="t1",
            message="查近三天告警",
            metadata={},
        )
        assert prepare_plan_confirm_gate(ctx) is None

    @patch("app.services.plan_confirm.settings")
    def test_disabled_switch(self, mock_settings):
        mock_settings.agent_plan_confirm_enabled = False
        ctx = assemble_context(
            thread_id="t1",
            message="查近三天告警然后导出",
            metadata={},
        )
        assert prepare_plan_confirm_gate(ctx) is None


class TestClearOrchestrationPending:
    def setup_method(self):
        clear_thread_orchestration("thread-test")

    def teardown_method(self):
        clear_thread_orchestration("thread-test")

    def test_clear_removes_bpmn_snapshot(self):
        set_thread_bpmn_snapshot("thread-test", {"graph": {"nodes": []}})
        assert get_thread_bpmn_snapshot("thread-test") is not None
        clear_thread_orchestration("thread-test")
        assert get_thread_bpmn_snapshot("thread-test") is None
