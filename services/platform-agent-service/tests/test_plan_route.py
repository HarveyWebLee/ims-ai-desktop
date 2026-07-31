"""Plan 路由决策表单测（生产化收敛）"""

from __future__ import annotations

from unittest.mock import patch

from app.services.plan_route import PlanExecutionMode, evaluate_plan_route


class TestEvaluatePlanRoute:
    def test_single_step_react(self):
        assert evaluate_plan_route("查近三天告警") == PlanExecutionMode.REACT

    def test_read_only_multi_step_react(self):
        """只读多步（导航+查询）走 ReAct，不触发显式 Plan。"""
        assert evaluate_plan_route("打开告警列表然后查近三天告警") == PlanExecutionMode.REACT

    def test_write_multi_step_explicit(self):
        """含写操作的多步走显式 Plan + plan_confirm。"""
        assert evaluate_plan_route("查近三天告警然后导出") == PlanExecutionMode.EXPLICIT_PLAN

    def test_implicit_query_export_explicit(self):
        assert evaluate_plan_route("查询近三天告警并导出") == PlanExecutionMode.EXPLICIT_PLAN

    @patch("app.services.plan_route.settings")
    def test_disabled_plan_confirm_always_react(self, mock_settings):
        mock_settings.agent_plan_confirm_enabled = False
        assert evaluate_plan_route("查近三天告警然后导出") == PlanExecutionMode.REACT

    @patch("app.services.plan_confirm.settings")
    @patch("app.services.plan_route.settings")
    def test_write_only_off_requires_confirm(self, mock_route_settings, mock_confirm_settings):
        """write_only=false 时只读多步也需显式 Plan。"""
        mock_route_settings.agent_plan_confirm_enabled = True
        mock_confirm_settings.agent_plan_confirm_enabled = True
        mock_confirm_settings.agent_plan_confirm_write_only = False
        assert (
            evaluate_plan_route("打开告警列表然后查近三天告警") == PlanExecutionMode.EXPLICIT_PLAN
        )
