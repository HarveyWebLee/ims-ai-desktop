"""LangGraph / LangChain RunnableConfig 构造辅助。"""

from __future__ import annotations

from typing import Any

from langchain_core.runnables import RunnableConfig


def thread_runnable_config(thread_id: str, **extra: Any) -> RunnableConfig:
    """按 thread_id 构造 LangGraph configurable 配置。"""
    configurable: dict[str, Any] = {"thread_id": thread_id}
    if extra:
        configurable.update(extra)
    return {"configurable": configurable}
