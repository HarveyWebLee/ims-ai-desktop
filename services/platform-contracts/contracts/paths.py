"""共享数据目录解析（catalog / navigation / device_action 等）。

解析顺序：``PLATFORM_MCP_DATA_DIR`` / ``CONTRACTS_DATA_DIR`` >
``bind_shared_data_dir`` > 本包 ``data/``。

**禁止**硬编码 monorepo 内其他服务工程的目录路径。
"""

from __future__ import annotations

import os
from pathlib import Path

from contracts.runtime_bind import resolve_shared_data_dir


def mcp_data_dir() -> Path:
    """返回共享 JSON 数据目录（不存在则创建）。"""
    return resolve_shared_data_dir()


def mcp_catalog_path() -> Path:
    """catalog.json 路径。

    优先 ``AGENT_CATALOG_PATH``（Agent export 覆盖）；否则 ``mcp_data_dir()/catalog.json``。
    """
    override = (os.environ.get("AGENT_CATALOG_PATH") or "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return mcp_data_dir() / "catalog.json"
