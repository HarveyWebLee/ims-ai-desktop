"""共享运行时配置。

- 默认：本模块 ``RuntimeSettings``（仅读**进程环境变量**，不读兄弟工程 `.env`）
- Agent / MCP 进程启动时应 ``bind_settings(宿主 settings)``，与宿主单例对齐
- **禁止**本包 ``import app`` / ``import platform_mcp``
- **禁止**硬编码 monorepo 内其他服务工程的目录路径
"""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic_settings import BaseSettings, SettingsConfigDict

from contracts.runtime_bind import bind_settings, get_bound_settings


class RuntimeSettings(BaseSettings):
    """未 bind 时的回退配置；路径类字段须由宿主 settings 或环境变量提供。"""

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file_encoding="utf-8",
        extra="ignore",
    )

    platform_api_base: str = "http://127.0.0.1:18001/api/app"
    agent_preflight_enabled: bool = True
    agent_debug_trace: bool = False
    # 平台 API 索引等；空表示未配置（宿主应 bind 带此字段的 settings）
    agent_data_dir: str = ""
    agent_service_root: str = ""


_runtime_settings = RuntimeSettings()


class _SettingsProxy:
    """优先读宿主 bind 的 settings；否则用本包 RuntimeSettings。"""

    def __getattr__(self, name: str) -> Any:
        bound = get_bound_settings()
        if bound is not None and hasattr(bound, name):
            return getattr(bound, name)
        return getattr(_runtime_settings, name)


settings = _SettingsProxy()

__all__ = ["RuntimeSettings", "bind_settings", "settings"]
