"""Platform MCP Server 配置。"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT = Path(__file__).resolve().parent.parent
_ENV = _ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    port: int = 8010
    host: str = "127.0.0.1"
    # monorepo 内 Agent 工程根（用于导入工具实现）
    agent_service_root: str = str((_ROOT.parent / "platform-agent-service").resolve())
    platform_api_base: str = "http://127.0.0.1:18001/api/app"


settings = Settings()
