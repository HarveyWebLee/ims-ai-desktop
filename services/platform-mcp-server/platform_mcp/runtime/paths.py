"""Platform MCP 数据目录（单一源）。"""

from __future__ import annotations

from pathlib import Path

# platform_mcp/data — catalog / navigation / device_action 唯一落盘处
_MCP_PKG = Path(__file__).resolve().parent.parent
_DATA_DIR = _MCP_PKG / "data"


def mcp_data_dir() -> Path:
    """返回 ``platform_mcp/data``（不存在则创建）。"""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    return _DATA_DIR


def mcp_catalog_path() -> Path:
    return mcp_data_dir() / "catalog.json"
