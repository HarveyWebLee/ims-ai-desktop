"""
平台工具注册表（v2）：Agent 图工具 **只** 来自 MCP Client + 本地 RAG。

零兼容：Platform MCP 不可达时不回退本机工具。
业务实现位于 ``contracts``，由 Platform MCP Server 进程执行。
"""

from __future__ import annotations

import logging

from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)

_authorized_tools: list[BaseTool] | None = None


def get_agent_tools() -> list[BaseTool]:
    """Agent 图绑定：MCP Client 工具 + retrieve_knowledge。不可达则抛错。"""
    global _authorized_tools
    if _authorized_tools is None:
        from app.mcp.client import get_mcp_tools_sync
        from app.mcp.local_tools import merge_agent_tools

        try:
            mcp_tools = get_mcp_tools_sync()
            if not mcp_tools:
                raise RuntimeError("MCP 返回空工具列表")
            _authorized_tools = merge_agent_tools(mcp_tools)
            logger.info(
                "agent tools bound via MCP: %s",
                [t.name for t in _authorized_tools],
            )
        except Exception as exc:
            logger.error("Platform MCP 不可用: %s", exc)
            raise RuntimeError(
                "Platform MCP 不可用。请先启动 platform-mcp-server（:8010）"
            ) from exc
    return list(_authorized_tools)


def reset_agent_tools_cache() -> None:
    global _authorized_tools
    _authorized_tools = None
    from app.mcp.client import clear_mcp_tools_cache

    clear_mcp_tools_cache()
