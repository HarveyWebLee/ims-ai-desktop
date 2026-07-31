"""
本地开发启动入口：uvicorn 服务器（可选热重载）

文件职责
--------
``uv run agent`` 的入口：默认打开 AgentTrace、配置日志、跑 ``app.main:app``。
热重载由 ``AGENT_RELOAD`` 控制（默认开；``scripts/all.sh`` 联调同样默认开）。

白话概念
--------
main.py =「应用本身」；dev.py =「开发时怎么舒服地跑起来」。
局域网可访问（host 0.0.0.0）。热重载仅监视 ``app/``，避免改 tests 触发重启。

在 Agent 流程中的位置
--------------------
  开发者终端
    → uv run agent（pyproject.toml scripts 指向本模块 main）
    → uvicorn 加载 app.main:app → lifespan 初始化持久化

和 main.py 的区别
-----------------
- main.py：定义 FastAPI ``app``，也可 ``python -m app.main``
- 本文件：开发快捷入口；setdefault ``AGENT_DEBUG_TRACE=true``（.env 可显式关掉）

如何运行
--------
  cd platform-agent-service
  uv run agent                 # 默认热重载（仅 app/）
  AGENT_RELOAD=0 uv run agent  # 关热重载

端口、Mock、DSN 等仍从 ``app.config.settings``（.env）读取。
"""

from __future__ import annotations

import os
from pathlib import Path

# 本地 dev 默认开启 [AgentTrace]（.env 显式设 AGENT_DEBUG_TRACE=false 可关闭）
os.environ.setdefault("AGENT_DEBUG_TRACE", "true")

import uvicorn  # ASGI 服务器，运行 FastAPI 应用

from app.config import settings
from app.utils.logging_setup import configure_agent_logging

# 仅监视业务包，避免 tests / scripts 批量改动触发热重载
_APP_DIR = Path(__file__).resolve().parent


def _env_flag(name: str, *, default: bool) -> bool:
    """读取开关型环境变量；未设置时用 default。"""
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def main() -> None:
    """
    启动 uvicorn，加载 app.main 里的 FastAPI 实例。

    host="0.0.0.0"：监听所有网卡，局域网可访问
    reload：默认开启；``AGENT_RELOAD=0`` 可关闭
    """
    configure_agent_logging(debug_trace=settings.agent_debug_trace)
    if settings.agent_debug_trace:
        print(
            "[AgentTrace] 排查日志已开启（AGENT_DEBUG_TRACE=true）；"
            "复现问题后请在终端搜索 AgentTrace",
            flush=True,
        )
    reload_enabled = _env_flag("AGENT_RELOAD", default=True)
    if reload_enabled:
        # 缩小监视面 + 短延迟合并连续保存，降低 Windows 上整栈被拖垮的概率
        print(
            "[agent] 热重载已开启（监视目录: app/）；关热重载请设 AGENT_RELOAD=0",
            flush=True,
        )
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=settings.port,
            reload=True,
            reload_dirs=[str(_APP_DIR)],
            reload_includes=["*.py"],
            reload_delay=0.5,
        )
        return

    print(
        "[agent] AGENT_RELOAD=0：已关闭热重载（端口保持稳定；改代码需重启进程）",
        flush=True,
    )
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
