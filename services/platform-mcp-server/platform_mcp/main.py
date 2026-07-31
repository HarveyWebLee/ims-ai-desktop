"""FastMCP Streamable HTTP 入口（可选热重载）。"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from platform_mcp.config import settings
from platform_mcp.server import mcp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("platform-mcp-server")

# 仅监视本包，避免无关目录触发重启
_PKG_DIR = Path(__file__).resolve().parent


def _env_flag(name: str, *, default: bool) -> bool:
    """读取开关型环境变量；未设置时用 default。"""
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def run() -> None:
    """
    启动 Platform MCP（Streamable HTTP）。

    热重载由 ``MCP_RELOAD`` 控制（默认开）；``scripts/all.sh`` 联调同样默认开。
    """
    reload_enabled = _env_flag("MCP_RELOAD", default=True)
    logger.info(
        "Platform MCP Server starting on http://%s:%s/mcp (agent_root=%s)",
        settings.host,
        settings.port,
        settings.agent_service_root,
    )

    if not reload_enabled:
        logger.info("MCP_RELOAD=0：已关闭热重载")
        mcp.run(transport="streamable-http", host=settings.host, port=settings.port)
        return

    import uvicorn

    logger.info("热重载已开启（监视目录: platform_mcp/）；关热重载请设 MCP_RELOAD=0")
    uvicorn.run(
        "platform_mcp.asgi:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        reload_dirs=[str(_PKG_DIR)],
        reload_includes=["*.py"],
        reload_delay=0.5,
    )


if __name__ == "__main__":
    run()
