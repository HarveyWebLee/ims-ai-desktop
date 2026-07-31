"""Phase D3 Trace 图构建单测"""

from __future__ import annotations

from app.services.trace_graph import build_trace_graph, enrich_trace_run


def test_build_trace_graph_empty():
    graph = build_trace_graph([])
    assert graph["nodes"] == []
    assert "empty" in graph["mermaid"]


def test_build_trace_graph_chain():
    events = [
        {"id": "e1", "kind": "user_message", "label": "用户输入", "ts": 1000},
        {"id": "e2", "kind": "tool_start", "label": "工具开始", "ts": 1001},
        {"id": "e3", "kind": "tool_end", "label": "工具完成", "ts": 1002},
        {"id": "e4", "kind": "done", "label": "结束", "ts": 1003},
    ]
    graph = build_trace_graph(events)
    assert len(graph["nodes"]) == 5  # start + 4 events
    assert len(graph["edges"]) == 4
    assert graph["edges"][0]["from"] == "__start__"
    assert graph["edges"][-1]["to"] == "e4"
    assert "flowchart TD" in graph["mermaid"]


def test_enrich_trace_run():
    run = {
        "thread_id": "t1",
        "run_id": "r1",
        "events": [{"id": "e1", "kind": "done", "label": "结束", "ts": 1}],
    }
    enriched = enrich_trace_run(run)
    assert "graph" in enriched
    assert enriched["graph"]["nodes"]
