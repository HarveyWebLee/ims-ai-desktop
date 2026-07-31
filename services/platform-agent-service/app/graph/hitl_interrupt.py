"""图内 HITL：统一经 LangGraph ``interrupt()`` 暂停，resume 后返回用户载荷。"""

from __future__ import annotations

from typing import Any


def interrupt_or_raise(payload: dict[str, Any]) -> Any:
    """
    在 LangGraph 节点或 MCP 工具包装器内暂停图，等待 ``Command(resume=...)``。

    参数:
        payload: 与前端 interrupt SSE 相同结构（type/tool/message/fields 等）

    返回:
        resume 时前端提交的载荷；拒绝时由调用方根据 ``is_hitl_reject`` 处理。
    """
    from langgraph.types import interrupt

    return interrupt(payload)
