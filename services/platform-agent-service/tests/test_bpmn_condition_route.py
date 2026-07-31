"""D1：plan_confirm 批准后 CONDITION 灰度路由单测。"""

from __future__ import annotations

from unittest.mock import patch

from app.graph.parent_graph import resolve_post_confirm_execution_route


def _conditional_doc() -> dict:
    return {
        "nodes": [
            {"id": "start_0", "type": "start", "data": {"title": "开始"}},
            {
                "id": "step_query",
                "type": "AUTO",
                "data": {"title": "查设备", "tool": "get_device_detail"},
            },
            {
                "id": "cond_online",
                "type": "CONDITION",
                "data": {
                    "title": "在线?",
                    "conditions": [
                        {
                            "key": "if_online",
                            "left": "onlineStatus",
                            "operator": "eq",
                            "right": "在线",
                        }
                    ],
                },
            },
            {
                "id": "step_open",
                "type": "AUTO",
                "data": {"title": "开门", "tool": "send_device_cmd"},
            },
            {
                "id": "step_history",
                "type": "AUTO",
                "data": {"title": "查历史", "tool": "query_device_history"},
            },
            {"id": "end_0", "type": "end", "data": {"title": "结束"}},
        ],
        "edges": [
            {"sourceNodeID": "start_0", "targetNodeID": "step_query"},
            {"sourceNodeID": "step_query", "targetNodeID": "cond_online"},
            {
                "sourceNodeID": "cond_online",
                "targetNodeID": "step_open",
                "sourcePortID": "if_online",
            },
            {
                "sourceNodeID": "cond_online",
                "targetNodeID": "step_history",
                "sourcePortID": "else",
            },
            {"sourceNodeID": "step_open", "targetNodeID": "end_0"},
            {"sourceNodeID": "step_history", "targetNodeID": "end_0"},
        ],
        "globalVariable": {"type": "object", "required": [], "properties": {}},
    }


def _linear_doc() -> dict:
    return {
        "nodes": [
            {"id": "start_0", "type": "start", "data": {"title": "开始"}},
            {
                "id": "step_q",
                "type": "AUTO",
                "data": {"title": "查告警", "tool": "query_alarms"},
            },
            {
                "id": "step_e",
                "type": "AUTO",
                "data": {"title": "导出", "tool": "download_file"},
            },
            {"id": "end_0", "type": "end", "data": {"title": "结束"}},
        ],
        "edges": [
            {"sourceNodeID": "start_0", "targetNodeID": "step_q"},
            {"sourceNodeID": "step_q", "targetNodeID": "step_e"},
            {"sourceNodeID": "step_e", "targetNodeID": "end_0"},
        ],
        "globalVariable": {"type": "object", "required": [], "properties": {}},
    }


class TestResolvePostConfirmExecutionRoute:
    def test_flag_off_keeps_plan_execute(self):
        with patch("app.config.settings") as mock_settings:
            mock_settings.agent_bpmn_condition_exec = False
            assert resolve_post_confirm_execution_route(_conditional_doc()) == "plan_execute"

    def test_flag_on_conditional_uses_bpmn_execute(self):
        with patch("app.config.settings") as mock_settings:
            mock_settings.agent_bpmn_condition_exec = True
            assert resolve_post_confirm_execution_route(_conditional_doc()) == "bpmn_execute"

    def test_flag_on_linear_stays_plan_execute(self):
        with patch("app.config.settings") as mock_settings:
            mock_settings.agent_bpmn_condition_exec = True
            assert resolve_post_confirm_execution_route(_linear_doc()) == "plan_execute"

    def test_none_or_invalid_stays_plan_execute(self):
        with patch("app.config.settings") as mock_settings:
            mock_settings.agent_bpmn_condition_exec = True
            assert resolve_post_confirm_execution_route(None) == "plan_execute"
            assert resolve_post_confirm_execution_route("x") == "plan_execute"
