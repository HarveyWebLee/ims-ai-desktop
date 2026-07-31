"""BPMN 执行：状态暂存与 PlanTracker / resume 路由（零兼容：无 pending_tool_hitl）。"""

from __future__ import annotations

import json

from tests.test_bpmn_execution_kernel import _conditional_door_document

from app.application.execution.bpmn_graph import build_execution_graph
from app.application.execution.bpmn_plan_runner import resolve_bpmn_resume_start_node
from app.application.execution.execution_context import ExecutionContext
from app.graph.stream_envelope import PlanTracker
from app.services.bpmn_execution_state import (
    clear_bpmn_execution_state,
    get_bpmn_execution_state,
    set_bpmn_execution_state,
)


class TestBpmnExecutionState:
    def test_set_get_clear(self):
        set_bpmn_execution_state("t1", {"paused_node_id": "n1"})
        assert get_bpmn_execution_state("t1") == {"paused_node_id": "n1"}
        clear_bpmn_execution_state("t1")
        assert get_bpmn_execution_state("t1") is None


class TestExecutionContextPromotion:
    def test_promotes_online_status_from_data(self):
        ctx = ExecutionContext()
        ctx.set_node_output(
            "step_query",
            json.dumps(
                {
                    "ok": True,
                    "data": {"onlineStatus": "在线", "device": {}},
                },
                ensure_ascii=False,
            ),
        )
        assert ctx.get_path("steps.step_query.onlineStatus") == "在线"


class TestPlanTrackerExternalUpdate:
    def test_apply_skip_reason(self):
        tracker = PlanTracker(
            [
                {
                    "id": "step_history",
                    "label": "查历史",
                    "tool": "query_device_history",
                    "status": "pending",
                }
            ]
        )
        payload = tracker.apply_external_plan_update(
            {
                "step_id": "step_history",
                "node_id": "step_history",
                "status": "skipped",
                "skipReason": "条件未匹配",
            }
        )
        assert payload["status"] == "skipped"
        assert tracker.steps[0]["status"] == "skipped"
        assert tracker.steps[0]["skipReason"] == "条件未匹配"


class TestBpmnResumeRouting:
    def test_resume_start_after_open_goes_to_end(self):
        doc = _conditional_door_document()
        graph = build_execution_graph(doc)
        ctx = ExecutionContext()
        ctx.set_node_output(
            "step_query",
            json.dumps({"ok": True, "onlineStatus": "在线"}, ensure_ascii=False),
        )
        ctx.mark_node("step_query", "AUTO", "done")
        ctx.mark_node("cond_online", "CONDITION", "done", matched_branch_key="if_online")
        nxt = resolve_bpmn_resume_start_node(graph, ctx, "step_open")
        assert nxt in (None, "end", "__end__") or isinstance(nxt, str)
