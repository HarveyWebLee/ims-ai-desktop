"""TraceCollector 过程时间线采集单测。"""

from __future__ import annotations

from app.services.trace_collector import TraceCollector


class TestTraceCollectorTurnTimeline:
    def test_context_rag_llm_tools_assistant(self):
        c = TraceCollector(thread_id="t1", run_id="r1")
        c.record_user_message("查一下告警")
        c.record_context_snapshot(
            {
                "model_id": "qwen",
                "run_mode": "confirm",
                "llm_user_message": "【参考知识】\n1. 告警说明\n\n使用者本轮消息\n\n查一下告警",
                "passive_rag_blocks": [
                    {"title": "告警手册", "source": "doc.md", "score": 0.9, "text": "如何查告警"}
                ],
                "skip_passive_rag": False,
                "rag_query": "查一下告警",
                "playbook_ids": [],
                "tool_names": ["query_alarms", "retrieve_knowledge"],
                "tool_subset_strategy": "domain",
                "domains": ["alarm"],
            }
        )
        c.record_sse("message", {"delta": "正在查询"})
        c.record_sse("message", {"delta": "告警…"})
        # flush before tool
        asst = c.flush_assistant_message(reason="before_tool_start")
        assert asst is not None
        assert "正在查询" in asst["detail"]["content"]

        start = c.record_sse(
            "tool_start",
            {"tool": "query_alarms", "args": {"status": "open", "token": "secret"}},
        )
        assert start is not None
        assert start["detail"]["channel"] == "mcp"
        assert start["detail"]["args"]["token"] == "***"

        end = c.record_sse(
            "tool_end",
            {
                "tool": "query_alarms",
                "result": '{"ok": true, "summary": "找到 2 条", "data": {"total": 2}}',
            },
        )
        assert end is not None
        assert end["detail"]["ok"] is True
        assert end["detail"]["channel"] == "mcp"

        rag_start = c.record_sse(
            "tool_start",
            {"tool": "retrieve_knowledge", "args": {"query": "告警"}},
        )
        assert rag_start is not None
        assert rag_start["detail"]["channel"] == "rag"

        c.record_sse("done", {"type": "done"})
        exported = c.export()
        kinds = [e["kind"] for e in exported["events"]]
        assert "user_message" in kinds
        assert "rag_passive" in kinds
        assert "llm_input" in kinds
        assert "assistant_message" in kinds
        assert "tool_start" in kinds
        assert "tool_end" in kinds
        assert "done" in kinds

    def test_rag_skipped(self):
        c = TraceCollector(thread_id="t1", run_id="r2")
        c.record_context_snapshot(
            {
                "llm_user_message": "播放广播",
                "passive_rag_blocks": [],
                "skip_passive_rag": True,
                "tool_names": [],
            }
        )
        kinds = [e["kind"] for e in c.events]
        assert "rag_passive" in kinds
        rag = next(e for e in c.events if e["kind"] == "rag_passive")
        assert rag["detail"].get("skipped") is True
