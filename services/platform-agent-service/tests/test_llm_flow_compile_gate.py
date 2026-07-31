"""P2：条件意图路由与门控 flow_document / IR.args 注入单测。"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.services.flow_ir import (
    FlowIr,
    FlowIrCondition,
    FlowIrTaskNode,
    flow_ir_to_params_by_tool,
    sanitize_flow_ir_node_args,
)
from app.services.llm_flow_compiler import (
    _extract_json_object,
    compile_flow_document,
)
from app.services.plan_confirm import prepare_plan_confirm_gate
from app.services.plan_route import PlanExecutionMode, evaluate_plan_route


def test_extract_json_object_from_fenced_and_prose():
    """DeepSeek thinking 兜底：从 markdown/夹杂文本中抽取 FlowIr JSON。"""
    data = _extract_json_object(
        '说明如下：\n```json\n{"entry":"a","nodes":[],"conditions":[]}\n```\n完'
    )
    assert data["entry"] == "a"
    data2 = _extract_json_object('{"entry":"b","nodes":[],"conditions":[]}')
    assert data2["entry"] == "b"
    # 单引号字面量（偶发）
    data3 = _extract_json_object("{'entry': 'c', 'nodes': [], 'conditions': []}")
    assert data3["entry"] == "c"
    # thinking 标签剥离
    data4 = _extract_json_object('<think>reasoning</think>{"entry":"d","nodes":[],"conditions":[]}')
    assert data4["entry"] == "d"


def _door_ir() -> FlowIr:
    return FlowIr(
        entry="step_query",
        nodes=[
            FlowIrTaskNode(
                id="step_query",
                tool="get_device_detail",
                label="查设备",
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
                label="查变量",
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


def test_sanitize_strips_leading_query_verb_from_device_name():
    cleaned = sanitize_flow_ir_node_args(
        "get_device_detail",
        {"device_name": "查看B口门禁", "junk": "x"},
    )
    assert cleaned == {"device_name": "B口门禁"}


def test_flow_ir_to_params_by_tool():
    params = flow_ir_to_params_by_tool(_door_ir())
    assert params["get_device_detail"]["device_name"] == "B口门禁"
    assert params["send_device_cmd"]["action"] == "开门"


def test_evaluate_plan_route_no_longer_forces_conditional_regex():
    """条件意图不再由 plan_route 正则强制 EXPLICIT_PLAN。"""
    with patch("app.services.plan_route.settings") as mock_settings:
        mock_settings.agent_plan_confirm_enabled = True
        mock_settings.agent_bpmn_llm_compile = True
        mock_settings.agent_bpmn_condition_exec = True
        mock_settings.agent_plan_confirm_write_only = True
        with patch(
            "app.services.plan_route.build_task_plan",
            return_value=None,
        ):
            mode = evaluate_plan_route("查716门禁，在线开门离线查历史")
            assert mode == PlanExecutionMode.REACT


def test_llm_flow_compile_gate_requires_both_flags():
    """AC-36：关 LLM_COMPILE 后门控关闭（仍可保留 CONDITION_EXEC）。"""
    from app.services.llm_flow_compiler import is_llm_flow_compile_enabled

    with patch("app.services.llm_flow_compiler.settings") as mock_settings:
        mock_settings.agent_bpmn_condition_exec = True
        mock_settings.agent_bpmn_llm_compile = False
        assert is_llm_flow_compile_enabled() is False
        mock_settings.agent_bpmn_llm_compile = True
        assert is_llm_flow_compile_enabled() is True


def test_prepare_plan_confirm_gate_merges_ir_params():
    doc = compile_flow_document(_door_ir())
    steps = [
        {
            "id": "step_query",
            "label": "查设备",
            "tool": "get_device_detail",
            "status": "pending",
        },
        {
            "id": "step_open",
            "label": "开门",
            "tool": "send_device_cmd",
            "status": "pending",
        },
        {
            "id": "step_vars",
            "label": "查变量",
            "tool": "query_device_variables",
            "status": "pending",
        },
    ]
    ctx = MagicMock()
    ctx.message = "查看B口门禁，在线开门，离线查历史"
    ctx.metadata = {}

    with patch("app.services.plan_confirm.settings") as mock_settings:
        mock_settings.agent_plan_confirm_enabled = True
        mock_settings.agent_plan_confirm_write_only = True
        gate = prepare_plan_confirm_gate(
            ctx,
            raw_plan=steps,
            flow_document=doc,
            ir_params_by_tool=flow_ir_to_params_by_tool(_door_ir()),
        )
    assert gate is not None
    assert gate.params_by_tool["get_device_detail"]["device_name"] == "B口门禁"
    assert gate.resume_hint.get("compile_source") == "llm_ir"
