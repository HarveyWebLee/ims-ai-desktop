"""
当前 Agent run 的请求级上下文（旁路观测用）。

在 wrap_stream_with_plan_trace 入口 set，abort / hitl_lifecycle 可读取 run_id，
不改写 HITL / SSE 主链。
"""

from __future__ import annotations

from contextvars import ContextVar

current_run_id: ContextVar[str | None] = ContextVar("current_run_id", default=None)
