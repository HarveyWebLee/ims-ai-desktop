"""BPMN 执行内核 P1 单测（迭代 1）。"""

from __future__ import annotations

import json

import pytest

from app.application.execution.bpmn_executor import execute_bpmn_graph
from app.application.execution.bpmn_graph import (
    build_execution_graph,
    flow_document_has_executable_conditions,
    iter_linear_task_node_ids,
)
from app.application.execution.condition_evaluator import (
    ConditionRule,
    evaluate_condition_rules,
    evaluate_operator,
    parse_condition_item,
    resolve_condition_left,
)
from app.application.execution.execution_context import ExecutionContext
from app.application.execution.plan_runner import execute_plan_steps
from app.services.bpmn_orchestration import plan_steps_to_flow_document


def _linear_flow_document(
    steps: list[dict],
) -> dict:
    """构造线性 AUTO 链画布。"""
    doc = plan_steps_to_flow_document(steps)
    return doc


def _conditional_door_document() -> dict:
    """门禁条件开门标准测试图。"""
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


async def _collect_events(
    flow_document: dict,
    *,
    stream_step=None,
    params_by_tool: dict | None = None,
) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    async for event in execute_bpmn_graph(
        flow_document,
        params_by_tool=params_by_tool or {},
        user_message="测试",
        stream_step=stream_step,
    ):
        events.append(event)
    return events


def _make_stream_step(results: dict[str, str]):
    """按工具名返回预设 JSON 结果。"""

    async def stream_step(node, params, user_message):
        _ = params, user_message
        tool = str(node.data.get("tool") or "")
        payload = results.get(tool, json.dumps({"ok": True}, ensure_ascii=False))
        yield ("tool_start", {"tool": tool, "args": {}})
        yield ("tool_end", {"tool": tool, "result": payload})

    return stream_step


class TestExecutionContext:
    def test_set_and_get_path(self):
        ctx = ExecutionContext()
        ctx.set_node_output(
            "step_query",
            json.dumps({"ok": True, "onlineStatus": "在线"}, ensure_ascii=False),
        )
        assert ctx.get_path("steps.step_query.onlineStatus") == "在线"
        assert ctx.get_path("steps.step_query.ok") is True

    def test_state_roundtrip(self):
        ctx = ExecutionContext(thread_id="t1", user_message="hello")
        ctx.set_node_output("n1", '{"ok":true}')
        ctx.mark_node("n1", "AUTO", "done")
        restored = ExecutionContext.from_state_dict(ctx.to_state_dict())
        assert restored.thread_id == "t1"
        assert restored.outputs["n1"]["ok"] is True
        assert restored.node_runtimes["n1"].status == "done"


class TestConditionEvaluator:
    def test_operators(self):
        assert evaluate_operator("在线", "eq", "在线")
        assert evaluate_operator("离线", "ne", "在线")
        assert evaluate_operator("abc在线xyz", "contains", "在线")
        assert evaluate_operator(None, "not_exists")
        assert evaluate_operator("", "not_exists")
        assert evaluate_operator(3, "gt", 1)

    def test_parse_flat_condition(self):
        rule = parse_condition_item(
            {"key": "if1", "left": "onlineStatus", "operator": "eq", "right": "在线"}
        )
        assert rule is not None
        assert rule.key == "if1"

    def test_resolve_left_with_last_task(self):
        rule = ConditionRule(key="k", left="onlineStatus", operator="eq", right="在线")
        expr = resolve_condition_left(rule, last_task_node_id="step_query")
        assert expr == "steps.step_query.onlineStatus"

    def test_evaluate_rules_match_and_else(self):
        ctx = ExecutionContext()
        ctx.set_node_output(
            "step_query",
            json.dumps({"onlineStatus": "离线"}, ensure_ascii=False),
        )
        rules = [
            ConditionRule(
                key="if_online", left="steps.step_query.onlineStatus", operator="eq", right="在线"
            )
        ]
        matched, err = evaluate_condition_rules(rules, ctx.get_path)
        assert err is None
        assert matched == "else"


class TestBpmnGraph:
    def test_build_linear_graph(self):
        doc = _linear_flow_document(
            [
                {"id": "1", "label": "查询", "tool": "query_alarms", "status": "pending"},
                {"id": "2", "label": "导出", "tool": "download_file", "status": "pending"},
            ]
        )
        graph = build_execution_graph(doc)
        assert graph.start_id == "start_0"
        task_ids = iter_linear_task_node_ids(graph)
        assert task_ids == ["1", "2"]
        assert flow_document_has_executable_conditions(doc) is False

    def test_build_conditional_graph(self):
        doc = _conditional_door_document()
        graph = build_execution_graph(doc)
        assert flow_document_has_executable_conditions(doc) is True
        assert graph.successor_by_port("cond_online", "if_online") == "step_open"
        assert graph.successor_by_port("cond_online", "else") == "step_history"


class TestBpmnExecutor:
    @pytest.mark.asyncio
    async def test_linear_graph_emits_tool_pairs_in_order(self):
        doc = _linear_flow_document(
            [
                {"id": "1", "label": "查询", "tool": "query_alarms", "status": "pending"},
                {"id": "2", "label": "导出", "tool": "download_file", "status": "pending"},
            ]
        )

        async def stream_step(node, params, user_message):
            _ = params, user_message
            tool = str(node.data.get("tool") or "")
            yield ("tool_start", {"tool": tool, "args": {}})
            yield ("tool_end", {"tool": tool, "result": json.dumps({"ok": True})})

        bpmn_events = await _collect_events(doc, stream_step=stream_step)
        bpmn_tools = [e[1]["tool"] for e in bpmn_events if e[0] == "tool_end"]
        assert bpmn_tools == ["query_alarms", "download_file"]

        plan_steps = [
            {"id": "1", "label": "查询", "tool": "query_alarms", "status": "pending"},
            {"id": "2", "label": "导出", "tool": "download_file", "status": "pending"},
        ]

        plan_events: list[tuple[str, dict]] = []

        async def plan_stream(step, params, user_message):
            _ = step, user_message
            tool = str(step.get("tool") or "")
            yield ("tool_start", {"tool": tool, "args": params})
            yield ("tool_end", {"tool": tool, "result": json.dumps({"ok": True})})

        async for event in execute_plan_steps(
            plan_steps,
            {},
            "测试",
            stream_step=plan_stream,
        ):
            plan_events.append(event)

        plan_tools = [e[1]["tool"] for e in plan_events if e[0] == "tool_end"]
        assert plan_tools == bpmn_tools

    @pytest.mark.asyncio
    async def test_condition_online_branch_skips_history(self):
        doc = _conditional_door_document()
        stream = _make_stream_step(
            {
                "get_device_detail": json.dumps(
                    {"ok": True, "onlineStatus": "在线"},
                    ensure_ascii=False,
                ),
                "send_device_cmd": json.dumps(
                    {"ok": True, "summary": "已下发"}, ensure_ascii=False
                ),
            }
        )
        events = await _collect_events(doc, stream_step=stream)

        tool_ends = [e[1]["tool"] for e in events if e[0] == "tool_end"]
        assert tool_ends == ["get_device_detail", "send_device_cmd"]
        assert "query_device_history" not in tool_ends

        skipped = [
            e[1] for e in events if e[0] == "plan_update" and e[1].get("status") == "skipped"
        ]
        assert any(s.get("node_id") == "step_history" for s in skipped)

    @pytest.mark.asyncio
    async def test_condition_offline_branch_skips_open(self):
        doc = _conditional_door_document()
        stream = _make_stream_step(
            {
                "get_device_detail": json.dumps(
                    {"ok": True, "onlineStatus": "离线"},
                    ensure_ascii=False,
                ),
                "query_device_history": json.dumps(
                    {"ok": True, "summary": "历史记录"},
                    ensure_ascii=False,
                ),
            }
        )
        events = await _collect_events(doc, stream_step=stream)

        tool_ends = [e[1]["tool"] for e in events if e[0] == "tool_end"]
        assert tool_ends == ["get_device_detail", "query_device_history"]
        assert "send_device_cmd" not in tool_ends

        skipped = [
            e[1] for e in events if e[0] == "plan_update" and e[1].get("status") == "skipped"
        ]
        assert any(s.get("node_id") == "step_open" for s in skipped)

    @pytest.mark.asyncio
    async def test_condition_node_marks_matched_branch(self):
        doc = _conditional_door_document()
        stream = _make_stream_step(
            {
                "get_device_detail": json.dumps(
                    {"ok": True, "onlineStatus": "在线"},
                    ensure_ascii=False,
                ),
                "send_device_cmd": json.dumps({"ok": True}, ensure_ascii=False),
            }
        )
        events = await _collect_events(doc, stream_step=stream)
        cond_updates = [
            e[1]
            for e in events
            if e[0] == "plan_update"
            and e[1].get("node_id") == "cond_online"
            and e[1].get("status") == "done"
        ]
        assert cond_updates
        assert cond_updates[-1].get("matchedBranchKey") == "if_online"
