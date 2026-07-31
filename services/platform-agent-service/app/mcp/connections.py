"""
MCP 连接配置：Platform MCP + 可选外部 MCP 服务器。
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


def build_mcp_connections(*, auth_token: str | None = None) -> dict[str, dict[str, Any]]:
    """
    构建 MultiServerMCPClient 连接表。

    始终包含 ``platform``；``AGENT_MCP_EXTRA_SERVERS_JSON`` 可追加外部 MCP。
    """
    headers: dict[str, str] = {}
    if auth_token:
        headers["Authorization"] = (
            auth_token if auth_token.lower().startswith("bearer ") else f"Bearer {auth_token}"
        )

    connections: dict[str, dict[str, Any]] = {
        "platform": {
            "transport": "streamable_http",
            "url": settings.platform_mcp_url,
            "headers": headers,
        }
    }

    raw = (settings.agent_mcp_extra_servers_json or "").strip()
    if not raw:
        return connections

    try:
        extra = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("AGENT_MCP_EXTRA_SERVERS_JSON 无效 JSON: %s", exc)
        return connections

    if not isinstance(extra, dict):
        logger.error("AGENT_MCP_EXTRA_SERVERS_JSON 须为对象 {name: connection}")
        return connections

    for name, conf in extra.items():
        key = str(name).strip()
        if not key or key == "platform":
            logger.warning("跳过非法/保留 MCP 服务器名: %s", name)
            continue
        if not isinstance(conf, dict):
            logger.warning("跳过无效 MCP 配置: %s", name)
            continue
        # 外部 HTTP 类可合并默认 Authorization（若未自带）
        transport = str(conf.get("transport") or conf.get("type") or "").lower()
        merged = dict(conf)
        if transport in {"http", "streamable_http", "streamable-http", "sse"} and headers:
            existing = dict(merged.get("headers") or {})
            if "Authorization" not in existing and "authorization" not in existing:
                existing.update(headers)
                merged["headers"] = existing
        connections[key] = merged
        logger.info("registered extra MCP server: %s", key)

    return connections
