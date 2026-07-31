"""
LLM Agent 路径：工具调用（供重试 / Plan Pipeline）。

生产路径经 **Platform MCP**（pipeline 包装，不再二次 authorize）。
零兼容：MCP 不可达时不回退 runtime 本机工具。

优先 ``ainvoke``（MCP StructuredTool 多为 async-only）；
``invoke_tool_sync`` 保留给测试与同步桥接场景。
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def get_tool_by_name(tool_name: str):
    """
    按名称查找 MCP 工具（Plan/Pipeline 缓存，无二次 authorize）。

    ``retrieve_knowledge`` 为本机 RAG 工具。
    """
    name = (tool_name or "").strip()
    if not name:
        return None

    if name == "retrieve_knowledge":
        from app.mcp.local_tools import build_retrieve_knowledge_tool

        return build_retrieve_knowledge_tool()

    try:
        from app.mcp.client import get_mcp_pipeline_tools_sync

        for tool in get_mcp_pipeline_tools_sync():
            if getattr(tool, "name", None) == name:
                return tool
    except Exception as exc:
        logger.error("get_tool_by_name: MCP 不可用 tool=%s err=%s", name, exc)
        return None
    return None


def _unknown_tool_result(tool_name: str) -> str:
    return json.dumps(
        {"ok": False, "summary": f"未知工具或 MCP 不可用：{tool_name}"},
        ensure_ascii=False,
    )


async def invoke_tool_async(tool_name: str, args: dict[str, Any] | None) -> str:
    """异步经 MCP 调用工具；HITL 中断异常原样抛出。"""
    tool = get_tool_by_name(tool_name)
    if tool is None:
        return _unknown_tool_result(tool_name)
    try:
        raw = await tool.ainvoke(args or {})
        return raw if isinstance(raw, str) else str(raw)
    except Exception as exc:
        from langgraph.errors import GraphInterrupt
        from platform_mcp.runtime.hitl import McpHitlSignal

        if isinstance(exc, (GraphInterrupt, McpHitlSignal)):
            raise
        logger.exception("工具 ainvoke 失败: tool=%s", tool_name)
        return json.dumps({"ok": False, "summary": str(exc)}, ensure_ascii=False)


def invoke_tool_sync(tool_name: str, args: dict[str, Any] | None) -> str:
    """同步经 MCP 调用工具；HITL / GraphInterrupt 原样抛出。"""
    tool = get_tool_by_name(tool_name)
    if tool is None:
        return _unknown_tool_result(tool_name)
    try:
        return tool.invoke(args or {})
    except Exception as exc:
        from langgraph.errors import GraphInterrupt
        from platform_mcp.runtime.hitl import McpHitlSignal

        if isinstance(exc, (GraphInterrupt, McpHitlSignal)):
            raise
        logger.exception("工具 invoke 失败: tool=%s", tool_name)
        return json.dumps({"ok": False, "summary": str(exc)}, ensure_ascii=False)
