"""
请求上下文模块：在 Agent 单次 HTTP 请求内透传身份与线程状态

文件职责
--------
用 ``contextvars.ContextVar`` 挂「当前请求专属」的变量，供工具与流适配器读取：
JWT、thread_id、HITL 确认 bypass、本轮压制工具、流式消息 skip、model_id 等。

白话概念
--------
同一进程可能同时服务多个值班员。不能把 JWT 放进全局变量，否则会串号。
ContextVar ≈ 每个请求自带的小书包：set 一次，深层 tool/helper 都能 get。

在 Agent 流程中的位置
--------------------
  chat / resume 入口 set ContextVar
    → Server Tools / platform_client.get()
    → 流结束 finally 里 safe_reset_contextvar

如何被调用
----------
  current_auth_token.set("Bearer xxx")
  token = current_auth_token.get()

主要 ContextVar
---------------
- current_auth_token：平台 Authorization
- current_thread_id：对话线程
- current_message_id：用户本轮 mid（SSE / 历史归属键）
- current_hitl_confirm_bypass：编排层已确认，跳过二次 ask_user_confirm
- current_turn_suppressed_tools：本轮忽略的 stale 工具（如误触发的 download_file）
- current_stream_message_skip：stream 仅发增量消息，避免简历历史 tool SSE
- current_model_id：worker 线程读 checkpoint 用
- current_run_mode：会话运行模式 readonly | confirm | autonomous
- current_plan_first：显式「先计划后执行」，覆盖 AI-first 旁路以走 plan_confirm
- current_user_utterance / current_recent_user_messages：本轮会话上下文（全工具共享，非导出专用）
- current_device_focus / current_alarm_focus：checkpoint 工具结果焦点（设备/告警空槽回填）
"""

from __future__ import annotations  # 允许在类型注解中引用尚未定义的类型（Python 3.7+ 特性）

# contextvars：Python 标准库，提供「按异步任务隔离」的变量
from contextvars import ContextVar, Token
from typing import Any

DEFAULT_RUN_MODE = "confirm"

# 会话上下文透传：单条用户句与近期列表的长度上限（HTTP 头 / 日志友好）
MAX_UTTERANCE_CHARS = 500
MAX_RECENT_USER_MESSAGES = 5
MAX_RECENT_MESSAGE_CHARS = 200

# 当前 Agent 请求携带的平台 Authorization 头（格式通常为 "Bearer <JWT>"）
# 与前端 App 的 requestTo 透传方式保持一致，供 platform_client 调用平台 API
current_auth_token: ContextVar[str | None] = ContextVar("current_auth_token", default=None)

# 当前对话线程 ID（thread_id），用于 pending/HITL、审计与工具执行上下文
current_thread_id: ContextVar[str | None] = ContextVar("current_thread_id", default=None)

# 用户本轮需求 ID（mid）：chat 生成、resume 回传；SSE / 历史投影按 mid 归属，禁止按工具名猜
current_message_id: ContextVar[str | None] = ContextVar("current_message_id", default=None)

# 编排层 HITL resume 续跑时跳过 ask_user_confirm 二次中断（用户已在前端确认）
current_hitl_confirm_bypass: ContextVar[bool] = ContextVar(
    "current_hitl_confirm_bypass",
    default=False,
)

# 用户拒绝 HITL 后的 drain：禁止 Agent 继续调用 MCP（避免取消后带着 JWT 重试写工具）
current_hitl_reject_drain: ContextVar[bool] = ContextVar(
    "current_hitl_reject_drain",
    default=False,
)

# 本轮 chat 应忽略的 stale 工具（如导航新意图下误触发的 download_file）
current_turn_suppressed_tools: ContextVar[frozenset[str]] = ContextVar(
    "current_turn_suppressed_tools",
    default=frozenset(),
)

# stream_events 开始时 checkpoint 已有消息条数，适配器仅处理增量（避免 resume/chat 重放历史 tool SSE）
current_stream_message_skip: ContextVar[int] = ContextVar(
    "current_stream_message_skip",
    default=0,
)

# 当前模型 ID（stream worker 线程内读取 checkpoint interrupt 用）
current_model_id: ContextVar[str | None] = ContextVar("current_model_id", default=None)

# 会话运行模式：readonly | confirm | autonomous（默认 confirm）
current_run_mode: ContextVar[str] = ContextVar("current_run_mode", default=DEFAULT_RUN_MODE)

# 显式 Plan：true 时即使 AI-first 也走 plan_confirm 门控（多步/写步骤先出计划再执行）
current_plan_first: ContextVar[bool] = ContextVar("current_plan_first", default=False)

# 本轮用户原话（chat 入口写入；resume 从 checkpoint 回填）。供 preflight / 消歧，不限导出。
current_user_utterance: ContextVar[str | None] = ContextVar(
    "current_user_utterance",
    default=None,
)

# 近几轮用户句（不含本轮）。与桌面 recent_user_messages 对齐，会话级共享。
current_recent_user_messages: ContextVar[tuple[str, ...]] = ContextVar(
    "current_recent_user_messages",
    default=(),
)

# 本线程最近设备焦点（由 checkpoint 工具结果解析；供全工具空槽回填与 HITL 预筛）
current_device_focus: ContextVar[Any] = ContextVar(
    "current_device_focus",
    default=None,
)

# 本线程最近告警焦点（由 checkpoint 工具结果解析；供导出/批量/详情空槽回填）
current_alarm_focus: ContextVar[Any] = ContextVar(
    "current_alarm_focus",
    default=None,
)


def normalize_run_mode(value: str | None) -> str:
    """将请求字段规范为合法 run_mode；非法或缺省 → confirm。"""
    mode = (value or "").strip().lower()
    if mode in ("readonly", "confirm", "autonomous"):
        return mode
    return DEFAULT_RUN_MODE


def normalize_user_utterance(value: str | None) -> str:
    """截断本轮用户原话。"""
    text = (value or "").strip()
    if len(text) > MAX_UTTERANCE_CHARS:
        return text[:MAX_UTTERANCE_CHARS]
    return text


def normalize_recent_user_messages(messages: list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    """规范化近期用户句：去空、截断条数与单条长度。"""
    out: list[str] = []
    for raw in messages or ():
        text = str(raw or "").strip()
        if not text:
            continue
        if len(text) > MAX_RECENT_MESSAGE_CHARS:
            text = text[:MAX_RECENT_MESSAGE_CHARS]
        out.append(text)
        if len(out) >= MAX_RECENT_USER_MESSAGES:
            break
    return tuple(out)


def encode_http_header_value(value: str) -> str:
    """
    将可能含非 ASCII 的字符串编码为 HTTP 头安全值。

    httpx / HTTP 规范要求头值为 latin-1；中文原话直接写入会触发
    ``UnicodeEncodeError: 'ascii' codec can't encode characters``。
    统一用百分号编码（``urllib.parse.quote``），MCP 侧对称 ``decode``。
    """
    from urllib.parse import quote

    return quote(value or "", safe="")


def decode_http_header_value(value: str | None) -> str:
    """还原 ``encode_http_header_value`` 后的头值；纯 ASCII 明文亦可透传。"""
    from urllib.parse import unquote

    return unquote(value or "")


def safe_reset_contextvar(
    var: ContextVar[Any],
    reset_token: Token[Any],
    *,
    label: str = "",
) -> None:
    """
    安全 reset ContextVar。

    async generator 在 GeneratorExit、LangGraph 子 Task 等场景下，
    finally 可能运行在与 set() 不同的 Context 中，直接 reset 会抛 ValueError。
    """
    import logging

    try:
        var.reset(reset_token)
    except ValueError:
        log = logging.getLogger(__name__)
        log.debug(
            "ContextVar %s reset 跳过（跨 Context，通常由 SSE 流中断引起）",
            label or getattr(var, "name", "unknown"),
        )
        try:
            from contracts.agent_debug import agent_debug

            agent_debug(
                "flow.context.reset_skipped",
                var=label or getattr(var, "name", "unknown"),
            )
        except Exception:
            pass
