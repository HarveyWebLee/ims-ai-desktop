"""
任务路由分类（chat / llm）

文件职责
--------
在真正调用大模型或工具之前，根据消息语义判定本轮走哪条执行路径。

在 Agent 流程中的位置
--------------------
  assemble_context
    → classify_task（本文件）→ TaskRoute
      → 父图 classify 节点分流
        ├─ AGENT_INTENT_AI_FIRST=true → 恒 react（默认）
        ├─ CHAT → chat_direct（create_agent tools=[]；仅 AI 优先关闭时）
        └─ LLM  → plan_confirm / device_gate / react / plan·bpmn（仅 AI 优先关闭时）

如何被调用
----------
- 父图 ``classify_node``；新消息经 ``stream_chat_core`` → ``stream_parent_graph``。
- ``stream_resume`` 不再重新 classify，一律 ``Command(resume)``。

关键概念（白话）
----------------
- Chat 短路：你好/你会做什么 → 直接聊天，不开工具链。
- LLM：默认路径，可能出 Plan、调工具、HITL 确认。
- 未配置 API Key 时由对话入口 `require_model_credentials` 直接报错，不再走 Mock。
"""

# ---------------------------------------------------------------------------
# 标准库
# ---------------------------------------------------------------------------
from __future__ import annotations

from enum import StrEnum

# ---------------------------------------------------------------------------
# 本项目
# ---------------------------------------------------------------------------
from app.graph.context import AgentContext


class TaskRoute(StrEnum):
    """
    编排层任务类型（字符串枚举，可直接打日志 / 序列化）。

    CHAT : Phase C1 纯对话短路
    LLM  : ReAct / Plan 工具路径
    """

    CHAT = "chat"  # Phase C1：纯对话短路，不调工具
    LLM = "llm"


def classify_task(ctx: AgentContext) -> TaskRoute:
    """
    根据消息语义决定执行路径。

    判定优先级（从上到下，命中即返回）:
        1. Chat：`is_chat_only_message` 判定为寒暄/能力咨询
        2. LLM：其余一律走工具 Agent

    参数:
        ctx: 本轮 AgentContext（主要用 ctx.message）

    返回:
        TaskRoute 枚举值。

    副作用:
        agent_debug 记录路由决策；不修改 store / checkpoint。
    """
    from app.services.chat_intent import is_chat_only_message

    if is_chat_only_message(ctx.message):
        route = TaskRoute.CHAT
    else:
        route = TaskRoute.LLM

    from platform_mcp.runtime.agent_debug import agent_debug

    agent_debug(
        "flow.route.decision",
        thread_id=ctx.thread_id,
        route=str(route),
        message_preview=(ctx.message or "")[:80],
        chat_only=(route == TaskRoute.CHAT),
    )
    return route
