"""P2：Flow IR 校验与 compile_flow_document 单测。"""

from __future__ import annotations

import pytest

from app.application.execution.bpmn_graph import (
    build_execution_graph,
    flow_document_has_executable_conditions,
)
from app.services.bpmn_orchestration import validate_flow_document
from app.services.flow_ir import (
    FlowIr,
    FlowIrCondition,
    FlowIrTaskNode,
    normalize_and_validate_flow_ir,
)
from app.services.llm_flow_compiler import (
    compile_flow_document,
    looks_like_conditional_intent,
)


def _door_ir() -> FlowIr:
    return FlowIr(
        entry="step_query",
        nodes=[
            FlowIrTaskNode(
                id="step_query",
                tool="get_device_detail",
                label="查设备",
            ),
            FlowIrTaskNode(
                id="step_open",
                tool="send_device_cmd",
                label="开门",
            ),
            FlowIrTaskNode(
                id="step_history",
                tool="query_device_variables",
                label="查变量",
            ),
        ],
        conditions=[
            FlowIrCondition(
                id="cond_online",
                label="在线?",
                left="onlineStatus",
                operator="eq",
                right="在线",
                then_target="step_open",
                else_target="step_history",
            )
        ],
    )


def test_normalize_expands_short_left_field():
    ir = normalize_and_validate_flow_ir(_door_ir())
    assert ir.conditions[0].left == "steps.step_query.onlineStatus"


def test_normalize_rejects_unknown_tool():
    ir = _door_ir()
    ir.nodes[0] = FlowIrTaskNode(
        id="step_query",
        tool="not_a_real_tool",
        label="x",
    )
    with pytest.raises(ValueError, match="未知工具"):
        normalize_and_validate_flow_ir(ir)


def test_normalize_rejects_illegal_left():
    ir = _door_ir()
    ir.conditions[0] = ir.conditions[0].model_copy(update={"left": "hackedField"})
    with pytest.raises(ValueError, match="白名单"):
        normalize_and_validate_flow_ir(ir)


def test_normalize_rejects_same_then_else():
    ir = _door_ir()
    ir.conditions[0] = ir.conditions[0].model_copy(
        update={"else_target": "step_open"},
    )
    with pytest.raises(ValueError, match="不能相同"):
        normalize_and_validate_flow_ir(ir)


def test_compile_door_ir_validates_and_has_else_port():
    doc = compile_flow_document(_door_ir())
    result = validate_flow_document(doc)
    assert result["valid"] is True, result.get("errors")
    assert flow_document_has_executable_conditions(doc) is True

    graph = build_execution_graph(doc)
    assert graph.successor_by_port("cond_online", "else") == "step_history"
    assert graph.successor_by_port("cond_online", "if_match") == "step_open"

    tools = {n.data.get("tool") for n in graph.nodes.values() if n.data.get("tool")}
    assert tools == {
        "get_device_detail",
        "send_device_cmd",
        "query_device_variables",
    }


def test_looks_like_conditional_intent():
    """保留轻量启发（仅 device_control 豁免等）；编译门控不再依赖它。"""
    assert looks_like_conditional_intent("查716门禁，在线开门离线查历史") is True
    assert looks_like_conditional_intent("查询昨天告警然后导出") is False
    assert looks_like_conditional_intent("你好") is False


def test_compile_preserves_sanitized_ir_args_on_nodes():
    ir = FlowIr(
        entry="step_query",
        nodes=[
            FlowIrTaskNode(
                id="step_query",
                tool="get_device_detail",
                label="查",
                args={"device_name": "查看B口门禁"},
            ),
            FlowIrTaskNode(
                id="step_open",
                tool="send_device_cmd",
                label="开门",
                args={"device_name": "B口门禁", "action": "开门"},
            ),
            FlowIrTaskNode(
                id="step_vars",
                tool="query_device_variables",
                label="变量",
                args={"device_name": "B口门禁"},
            ),
        ],
        conditions=[
            FlowIrCondition(
                id="cond_online",
                label="在线?",
                left="onlineStatus",
                operator="eq",
                right="在线",
                then_target="step_open",
                else_target="step_vars",
            )
        ],
    )
    doc = compile_flow_document(ir)
    query = next(n for n in doc["nodes"] if n["id"] == "step_query")
    assert query["data"]["args"]["device_name"] == "B口门禁"
