"""P1-3 知识检索 Subagent：摘要回主 agent、不含全文 hits。"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from app.mcp.local_tools import build_retrieve_knowledge_tool
from app.rag.context import format_rag_section
from app.services.subagent.knowledge_research import extractive_summary, research_knowledge


def test_extractive_summary_truncates() -> None:
    blocks = [
        {
            "title": "告警确认",
            "source": "a.md",
            "text": "x" * 500,
            "score": 0.9,
        }
    ]
    text = extractive_summary("如何确认告警", blocks, snippet_chars=40)
    assert "告警确认" in text
    assert "…" in text
    assert len(text) < 500


def test_format_rag_section_truncates() -> None:
    section = format_rag_section(
        [{"title": "T", "source": "s.md", "text": "abcdefghijklmnopqrstuvwxyz0123456789"}],
        snippet_chars=30,
    )
    assert "T" in section
    assert "…" in section
    assert "0123456789" not in section


def test_research_knowledge_no_full_hits(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "agent_subagent_knowledge_enabled", True)
    monkeypatch.setattr(settings, "agent_subagent_knowledge_llm", False)
    blocks = [
        {
            "title": "导出报表",
            "source": "export.md",
            "text": "第一步打开导出页面，选择时间范围后下载。",
            "score": 0.88,
        }
    ]
    with patch(
        "app.rag.context.retrieve_knowledge_blocks",
        return_value=blocks,
    ):
        payload = research_knowledge("如何导出告警")
    assert payload["ok"] is True
    assert "导出" in payload["summary"] or "报表" in payload["summary"]
    data = payload["data"]
    assert data["hit_count"] == 1
    assert data["mode"] == "extractive"
    assert "hits" not in data
    assert data["sources"][0]["title"] == "导出报表"
    # 摘要不应等于超长全文堆叠
    assert "hits" not in json.dumps(payload)


def test_retrieve_knowledge_tool_uses_subagent(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "agent_subagent_knowledge_enabled", True)
    monkeypatch.setattr(settings, "agent_subagent_knowledge_llm", False)
    with patch(
        "app.rag.context.retrieve_knowledge_blocks",
        return_value=[
            {"title": "导航", "source": "n.md", "text": "使用 navigate_to 打开页面。", "score": 0.7}
        ],
    ):
        raw = build_retrieve_knowledge_tool().invoke({"query": "怎么打开设备页", "top_k": 2})
    parsed = json.loads(raw)
    assert parsed["ok"] is True
    assert "hits" not in parsed.get("data", {})
    assert parsed["data"]["hit_count"] == 1


def test_research_llm_fallback_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "agent_subagent_knowledge_enabled", True)
    monkeypatch.setattr(settings, "agent_subagent_knowledge_llm", True)
    blocks = [{"title": "A", "source": "a.md", "text": "内容甲", "score": 0.5}]
    with (
        patch("app.rag.context.retrieve_knowledge_blocks", return_value=blocks),
        patch(
            "app.services.subagent.knowledge_research._llm_summarize",
            return_value=None,
        ),
    ):
        payload = research_knowledge("问甲")
    assert payload["data"]["mode"] == "extractive"
    assert "内容甲" in payload["summary"] or "A" in payload["summary"]
