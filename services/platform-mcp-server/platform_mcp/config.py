"""Platform MCP Server 配置。"""

from pathlib import Path
from typing import ClassVar

from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT = Path(__file__).resolve().parent.parent
_PKG_DIR = Path(__file__).resolve().parent
_PKG_DATA = _PKG_DIR / "data"
_REPO_ROOT = _ROOT.parent.parent
_ENV_SHARED = _REPO_ROOT / ".env.shared"
_ENV = _ROOT / ".env"
_DEFAULT_AGENT_ROOT = (_ROOT.parent / "platform-agent-service").resolve()


def _env_files() -> tuple[str, ...]:
    """shared 在前、本服务在后（后者覆盖同名键）。"""
    files: list[str] = []
    if _ENV_SHARED.is_file():
        files.append(str(_ENV_SHARED))
    if _ENV.is_file():
        files.append(str(_ENV))
    return tuple(files)


class Settings(BaseSettings):
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=_env_files() or None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    port: int = 8010
    host: str = "127.0.0.1"
    # monorepo 内 Agent 工程根（catalog 回退、平台 API 索引）
    agent_service_root: str = str(_DEFAULT_AGENT_ROOT)
    # 平台 API 索引 JSON（默认 Agent app/data）
    agent_data_dir: str = str((_DEFAULT_AGENT_ROOT / "app" / "data").resolve())
    platform_api_base: str = "http://127.0.0.1:18001/api/app"


settings = Settings()

# 将 MCP 配置与共享 data 目录注入 contracts（禁止 contracts 反向依赖本包路径）
from contracts.runtime_bind import bind_settings, bind_shared_data_dir  # noqa: E402

bind_shared_data_dir(_PKG_DATA)
bind_settings(settings)
