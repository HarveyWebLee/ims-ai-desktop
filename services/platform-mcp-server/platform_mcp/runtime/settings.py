"""平台工具运行时配置。

- 在 Agent 进程内：优先读 ``app.config.settings``（含单测 monkeypatch）
- 在 MCP Server 进程：读本模块 ``RuntimeSettings``（.env）
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict

_MCP_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV = _MCP_ROOT / ".env"
_AGENT_ROOT = (_MCP_ROOT.parent / "platform-agent-service").resolve()
_AGENT_ENV = _AGENT_ROOT / ".env"
_DEFAULT_AGENT_DATA = (_AGENT_ROOT / "app" / "data").resolve()


class RuntimeSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(_ENV), str(_AGENT_ENV)),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    platform_api_base: str = "http://127.0.0.1:18001/api/app"
    agent_preflight_enabled: bool = True
    agent_debug_trace: bool = False
    agent_data_dir: str = str(_DEFAULT_AGENT_DATA)
    agent_service_root: str = str(_AGENT_ROOT)


_runtime_settings = RuntimeSettings()


class _SettingsProxy:
    """Agent 进程委托 app.config；MCP 进程用 RuntimeSettings。"""

    def __getattr__(self, name: str) -> Any:
        try:
            from app.config import settings as agent_settings

            if hasattr(agent_settings, name):
                return getattr(agent_settings, name)
        except ImportError:
            pass
        return getattr(_runtime_settings, name)


settings = _SettingsProxy()
