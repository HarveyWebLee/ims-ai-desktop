"""
应用日志配置模块

文件职责
--------
让 ``app.*`` / ``[AgentTrace]`` 日志出现在 uvicorn 终端。
uvicorn 默认偏 access log，业务 logger 需单独挂 StreamHandler。

白话概念
--------
不配置时你在代码里 ``logger.info`` 可能「写了但看不见」；
本模块在启动时把 app 命名空间接到 stderr。

在 Agent 流程中的位置
--------------------
  app.main lifespan / app.dev.main
    → configure_agent_logging(debug_trace=settings.agent_debug_trace)
"""

from __future__ import annotations

import logging
import sys


def configure_agent_logging(*, debug_trace: bool) -> None:
    """
    配置 app 命名空间日志输出。

    参数
    ----
    debug_trace : bool
        True 时 level=INFO 并确保 StreamHandler；False 时多为 WARNING。

    说明
    ----
    uvicorn 默认只打印 access log；app.* 的 logger.info 需单独挂 StreamHandler。
    """
    level = logging.INFO if debug_trace else logging.WARNING
    formatter = logging.Formatter("%(levelname)s:     %(name)s | %(message)s")

    for name in ("app", "app.agent_debug", "app.main"):
        log = logging.getLogger(name)
        log.setLevel(level)
        if debug_trace and not any(isinstance(h, logging.StreamHandler) for h in log.handlers):
            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(formatter)
            log.addHandler(handler)
        # 避免向 root 重复输出
        log.propagate = False
