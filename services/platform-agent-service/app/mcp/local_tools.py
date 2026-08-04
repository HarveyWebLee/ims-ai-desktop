"""
本地 RAG 工具：retrieve_knowledge（Qdrant）。

不经 Platform MCP，由 Agent 进程直接注册到工具列表。
P1-3：经知识检索 Subagent 返回摘要，全文 hits 不回灌主对话。
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import StructuredTool


def build_retrieve_knowledge_tool() -> StructuredTool:
    """构建 retrieve_knowledge LangChain Tool（Subagent 摘要出口）。"""

    def _run(query: str, top_k: int = 4) -> str:
        from app.services.subagent import research_knowledge

        payload = research_knowledge(query, top_k=top_k)
        return json.dumps(payload, ensure_ascii=False)

    return StructuredTool.from_function(
        func=_run,
        name="retrieve_knowledge",
        description=(
            "从平台知识库（Qdrant）语义检索操作指引与能力说明。"
            "返回检索摘要与来源标题（不含长原文），用于回答产品/流程类问题。"
        ),
    )


def merge_agent_tools(mcp_tools: list[Any]) -> list[Any]:
    """MCP 工具 + 本地 retrieve_knowledge。"""
    names = {t.name for t in mcp_tools}
    out = list(mcp_tools)
    local = build_retrieve_knowledge_tool()
    if local.name not in names:
        out.append(local)
    return out
