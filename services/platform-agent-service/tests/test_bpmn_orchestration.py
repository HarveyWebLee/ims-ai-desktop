"""BPMN 编排服务单测"""

from __future__ import annotations

import pytest

from app.services.bpmn_orchestration import (
    flow_document_to_plan_steps,
    merge_bpmn_steps_with_previous,
    plan_steps_to_flow_document,
    validate_flow_document,
)


def test_plan_steps_roundtrip():
    steps = [
        {"id": "1", "label": "查询", "tool": "query_alarms", "status": "awaiting_confirm"},
        {"id": "2", "label": "导出", "tool": "download_file", "status": "awaiting_confirm"},
    ]
    doc = plan_steps_to_flow_document(steps)
    extracted = flow_document_to_plan_steps(doc)
    assert len(extracted) == 2
    assert extracted[0]["tool"] == "query_alarms"


def test_merge_preserves_skipped():
    previous = [
        {"id": "1", "label": "查询", "tool": "query_alarms", "status": "skipped"},
        {"id": "2", "label": "导出", "tool": "download_file", "status": "awaiting_confirm"},
    ]
    extracted = [
        {"id": "1", "label": "查询", "tool": "query_alarms", "status": "pending"},
        {"id": "2", "label": "导出", "tool": "download_file", "status": "pending"},
    ]
    merged = merge_bpmn_steps_with_previous(extracted, previous)
    assert merged[0]["status"] == "skipped"


def test_validate_requires_task_node():
    doc = plan_steps_to_flow_document([])
    # 无任务节点：仅 start/end
    doc["nodes"] = [n for n in doc["nodes"] if n["type"] in ("start", "end")]
    result = validate_flow_document(doc)
    assert result["valid"] is False


def test_validate_task_node_requires_tool():
    steps = [
        {"id": "1", "label": "查询", "tool": "query_alarms", "status": "awaiting_confirm"},
    ]
    doc = plan_steps_to_flow_document(steps)
    for node in doc["nodes"]:
        if node.get("id") == "1":
            node["data"]["tool"] = ""
    result = validate_flow_document(doc)
    assert result["valid"] is False
    assert any("未绑定 Agent 工具" in e for e in result["errors"])


def test_flow_document_without_deleted_step():
    """删除导出节点后，画布解析结果不应包含被删步骤。"""
    steps = [
        {"id": "1", "label": "查询", "tool": "query_alarms", "status": "awaiting_confirm"},
        {"id": "2", "label": "导出", "tool": "download_file", "status": "awaiting_confirm"},
    ]
    doc = plan_steps_to_flow_document(steps)
    # 模拟用户删除导出节点并重连 start → 查询 → end
    doc["nodes"] = [n for n in doc["nodes"] if n.get("id") != "2"]
    doc["edges"] = [
        {"sourceNodeID": "start_0", "targetNodeID": "1"},
        {"sourceNodeID": "1", "targetNodeID": "end_0"},
    ]
    extracted = flow_document_to_plan_steps(doc)
    assert len(extracted) == 1
    assert extracted[0]["tool"] == "query_alarms"
    merged = merge_bpmn_steps_with_previous(extracted, steps)
    assert len(merged) == 1
    assert merged[0]["tool"] == "query_alarms"


def test_validate_rejects_condition_three_branch():
    """出边 >2 仍拒绝；双分支无 else 亦拒绝。"""
    doc = {
        "nodes": [
            {"id": "start_0", "type": "start", "data": {"title": "开始"}},
            {"id": "cond_1", "type": "CONDITION", "data": {"title": "条件节点"}},
            {"id": "task_a", "type": "AUTO", "data": {"title": "查询", "tool": "query_alarms"}},
            {"id": "task_b", "type": "AUTO", "data": {"title": "导出", "tool": "download_file"}},
            {"id": "end_0", "type": "end", "data": {"title": "结束"}},
        ],
        "edges": [
            {"sourceNodeID": "start_0", "targetNodeID": "cond_1"},
            {"sourceNodeID": "cond_1", "targetNodeID": "task_a"},
            {"sourceNodeID": "cond_1", "targetNodeID": "task_b"},
            {"sourceNodeID": "task_a", "targetNodeID": "end_0"},
            {"sourceNodeID": "task_b", "targetNodeID": "end_0"},
        ],
        "globalVariable": {"type": "object", "required": [], "properties": {}},
    }
    result = validate_flow_document(doc)
    assert result["valid"] is False
    assert any("else" in e for e in result["errors"])


def test_validate_accepts_condition_if_else_branch():
    doc = {
        "nodes": [
            {"id": "start_0", "type": "start", "data": {"title": "开始"}},
            {"id": "cond_1", "type": "CONDITION", "data": {"title": "条件节点"}},
            {"id": "task_a", "type": "AUTO", "data": {"title": "查询", "tool": "query_alarms"}},
            {"id": "task_b", "type": "AUTO", "data": {"title": "导出", "tool": "download_file"}},
            {"id": "end_0", "type": "end", "data": {"title": "结束"}},
        ],
        "edges": [
            {"sourceNodeID": "start_0", "targetNodeID": "cond_1"},
            {
                "sourceNodeID": "cond_1",
                "targetNodeID": "task_a",
                "sourcePortID": "if_online",
            },
            {
                "sourceNodeID": "cond_1",
                "targetNodeID": "task_b",
                "sourcePortID": "else",
            },
            {"sourceNodeID": "task_a", "targetNodeID": "end_0"},
            {"sourceNodeID": "task_b", "targetNodeID": "end_0"},
        ],
        "globalVariable": {"type": "object", "required": [], "properties": {}},
    }
    result = validate_flow_document(doc)
    assert result["valid"] is True
    steps = flow_document_to_plan_steps(doc)
    assert len(steps) == 2
    assert {s["tool"] for s in steps} == {"query_alarms", "download_file"}


def test_validate_rejects_unknown_tool():
    steps = [
        {"id": "1", "label": "查询", "tool": "query_alarms", "status": "awaiting_confirm"},
    ]
    doc = plan_steps_to_flow_document(steps)
    for node in doc["nodes"]:
        if node.get("id") == "1":
            node["data"]["tool"] = "not_a_registered_tool"
    result = validate_flow_document(doc)
    assert result["valid"] is False
    assert any("未注册工具" in e for e in result["errors"])


def test_flow_document_to_plan_steps_rejects_condition_without_else():
    doc = {
        "nodes": [
            {"id": "start_0", "type": "start", "data": {"title": "开始"}},
            {"id": "cond_1", "type": "CONDITION", "data": {"title": "条件节点"}},
            {"id": "task_a", "type": "AUTO", "data": {"title": "查询", "tool": "query_alarms"}},
            {"id": "task_b", "type": "AUTO", "data": {"title": "导出", "tool": "download_file"}},
            {"id": "end_0", "type": "end", "data": {"title": "结束"}},
        ],
        "edges": [
            {"sourceNodeID": "start_0", "targetNodeID": "cond_1"},
            {"sourceNodeID": "cond_1", "targetNodeID": "task_a"},
            {"sourceNodeID": "cond_1", "targetNodeID": "task_b"},
        ],
        "globalVariable": {"type": "object", "required": [], "properties": {}},
    }
    with pytest.raises(ValueError, match="else 出口"):
        flow_document_to_plan_steps(doc)


def test_llm_step_roundtrip_preserves_model_id():
    steps = [
        {
            "id": "llm_1",
            "label": "通义闪",
            "modelId": "qwen3.5-35b-a3b",
            "status": "pending",
        }
    ]
    doc = plan_steps_to_flow_document(steps)
    llm_nodes = [n for n in doc["nodes"] if n.get("type") == "LLM"]
    assert len(llm_nodes) == 1
    assert llm_nodes[0]["data"]["modelId"] == "qwen3.5-35b-a3b"
    back = flow_document_to_plan_steps(doc)
    assert back[0]["modelId"] == "qwen3.5-35b-a3b"
    assert back[0].get("tool") in (None, "")


def test_validate_rejects_llm_without_model_id():
    doc = {
        "nodes": [
            {"id": "start_0", "type": "start", "data": {"title": "开始"}},
            {"id": "llm_1", "type": "LLM", "data": {"title": "LLM"}},
            {"id": "end_0", "type": "end", "data": {"title": "结束"}},
        ],
        "edges": [
            {"sourceNodeID": "start_0", "targetNodeID": "llm_1"},
            {"sourceNodeID": "llm_1", "targetNodeID": "end_0"},
        ],
        "globalVariable": {"type": "object", "required": [], "properties": {}},
    }
    result = validate_flow_document(doc)
    assert result["valid"] is False
    assert any("modelId" in e for e in result["errors"])
