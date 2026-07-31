"""
本地 RAG 工具：retrieve_knowledge（Qdrant）。

不经 Platform MCP，由 Agent 进程直接注册到工具列表。
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import StructuredTool


def build_retrieve_knowledge_tool() -> StructuredTool:
    """构建 retrieve_knowledge LangChain Tool。"""

    def _run(query: str, top_k: int = 4) -> str:
        from app.rag.context import retrieve_knowledge_blocks

        blocks = retrieve_knowledge_blocks(query, top_k=top_k)
        if not blocks:
            return json.dumps(
                {
                    "ok": True,
                    "summary": "未检索到相关知识（向量库未配置或无命中）",
                    "data": {"hits": []},
                },
                ensure_ascii=False,
            )
        return json.dumps(
            {
                "ok": True,
                "summary": f"检索到 {len(blocks)} 条相关知识",
                "data": {"hits": blocks},
            },
            ensure_ascii=False,
        )

    return StructuredTool.from_function(
        func=_run,
        name="retrieve_knowledge",
        description="从平台知识库（Qdrant）语义检索操作指引与能力说明，用于回答产品/流程类问题。",
    )


def merge_agent_tools(mcp_tools: list[Any]) -> list[Any]:
    """MCP 工具 + 本地 retrieve_knowledge。"""
    names = {t.name for t in mcp_tools}
    out = list(mcp_tools)
    local = build_retrieve_knowledge_tool()
    if local.name not in names:
        out.append(local)
    return out
