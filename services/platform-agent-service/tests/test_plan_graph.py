"""Phase D4 Plan 图构建与编排单测"""

from __future__ import annotations

from app.services.plan_graph import (
    build_plan_graph,
    build_plan_sse_payload,
    normalize_approved_plan_steps,
)


def test_build_plan_graph_chain():
    steps = [
        {"id": "1", "label": "查询", "tool": "query_alarms", "status": "pending"},
        {"id": "2", "label": "导出", "tool": "download_file", "status": "pending"},
    ]
    graph = build_plan_graph(steps)
    assert len(graph["nodes"]) == 3  # start + 2
    assert len(graph["edges"]) == 2
    assert graph["nodes"][1]["tool"] == "query_alarms"
    assert "flowchart LR" in graph["mermaid"]


def test_normalize_approved_plan_steps_skips():
    steps = [
        {"id": "1", "label": "查询", "tool": "query_alarms", "status": "awaiting_confirm"},
        {"id": "2", "label": "导出", "tool": "download_file", "status": "skipped"},
    ]
    out = normalize_approved_plan_steps(steps)
    assert len(out) == 1
    assert out[0]["tool"] == "query_alarms"
    assert out[0]["status"] == "pending"


def test_build_plan_sse_payload_includes_graph_and_flow_document():
    steps = [
        {"id": "1", "label": "查询", "tool": "query_alarms", "status": "pending"},
    ]
    flow_doc = {"nodes": [{"id": "start_0"}], "edges": []}
    payload = build_plan_sse_payload(steps, flow_document=flow_doc)
    assert payload["steps"] == steps
    assert "graph" in payload
    assert payload["flow_document"] == flow_doc
