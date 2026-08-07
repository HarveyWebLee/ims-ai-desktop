"""
单次对话上下文组装（Phase A：从 builder 抽离）

文件职责
--------
把前端 SSE 请求里的「原始用户句 + metadata + 近期消息」整理成
不可变的 `AgentContext`，供后续路由、Plan、执行循环统一读取。

在 Agent 流程中的位置
--------------------
  chat.py → stream_chat → stream_chat_core
    → assemble_context（本文件）
      → classify_task / prepare_plan_confirm / 父图节点

如何被调用
----------
- 主路径：`application.conversation.chat.stream_chat_core` 每轮新消息必调
- resume 路径通常手工构造轻量 `AgentContext`（仅 thread + 上次用户句），不经过本模块

关键概念（白话）
----------------
- message：用户屏幕上打的那句话（展示/意图判定用）。
- llm_user_message：真正喂给大模型的文本，可能拼上了「当前页面路径」、近期对话摘要等。
- metadata：前端附带上下文，如 `current_path`（用户正在看哪一页）。
- recent_user_messages：前端维护的近几轮用户句，用于意图消歧（不一定依赖 checkpoint）。
"""

# ---------------------------------------------------------------------------
# 标准库
# ---------------------------------------------------------------------------
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AgentContext:
    """
    一次 chat 请求的编排上下文（不可变 dataclass）。

    frozen=True：组装后字段不可改，避免中途误改「本轮真实用户句」。
    """

    thread_id: str
    message: str
    llm_user_message: str
    metadata: dict[str, Any] = field(default_factory=dict)
    recent_user_messages: list[str] = field(default_factory=list)
    # 可观测旁路：被动 RAG / Playbook（不进业务主链）
    passive_rag_blocks: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    skip_passive_rag: bool = False
    playbook_ids: tuple[str, ...] = field(default_factory=tuple)

    @property
    def current_path(self) -> str:
        """当前前端页面路径（无则空字符串）。"""
        return str(self.metadata.get("current_path") or "").strip()


def assemble_context(
    *,
    thread_id: str,
    message: str,
    metadata: dict[str, Any] | None = None,
    recent_user_messages: list[str] | None = None,
) -> AgentContext:
    """
    组装上下文：合并 metadata、近期消息，生成 LLM 用户消息。

    参数:
        thread_id: 会话 ID
        message: 用户原始输入
        metadata: 可选页面上下文
        recent_user_messages: 前端传来的近期用户句；会经意图解析裁剪

    返回:
        AgentContext 实例。

    副作用:
        打 debug 日志（`flow.context.assembled`）；不写 session_store / checkpoint。

    业务规则:
        若 `resolve_recent_messages_for_intent` 返回 intent_note（例如「刚取消导出」），
        会前置拼到 llm_user_message，帮助模型别再误触发导出工具。
        纯设备控制意图跳过被动 RAG，避免「播放广播」等命中前端播报文档导致空口等待。
    """
    from app.services.prompt_assembly import (
        USER_TURN_SECTION_HEADER,
        build_device_control_intent_note,
        build_howto_guidance_intent_note,
        build_llm_user_message,
        build_multiturn_context_intent_note,
        parse_device_control_action,
        resolve_recent_messages_for_intent,
    )

    meta = dict(metadata or {})
    prior, intent_note = resolve_recent_messages_for_intent(message, recent_user_messages)
    llm_message = build_llm_user_message(
        message,
        metadata=meta,
        recent_user_messages=prior,
    )
    # 意图注记前置，优先级高于路径注入正文
    notes = [
        n
        for n in (
            intent_note,
            build_multiturn_context_intent_note(message, recent_user_messages=prior),
            build_howto_guidance_intent_note(message),
            build_device_control_intent_note(message, recent_user_messages=prior),
        )
        if n
    ]
    if notes:
        # 保证有「使用者本轮消息」分段，便于历史还原剥离注记
        if USER_TURN_SECTION_HEADER not in llm_message:
            llm_message = f"{USER_TURN_SECTION_HEADER}\n\n{message.strip()}"
        llm_message = "\n\n".join(notes) + f"\n\n{llm_message}"

    # Qdrant RAG：每轮被动注入（失败不阻断）。
    # 纯设备控制意图跳过：避免「播放广播」等命中前端播报方案文档，诱导模型空口「等待结果」而不调工具。
    skip_passive_rag = parse_device_control_action(message) is not None
    passive_rag_blocks: list[dict[str, Any]] = []
    if not skip_passive_rag:
        try:
            from app.rag.context import format_rag_section, retrieve_knowledge_blocks

            rag_blocks = retrieve_knowledge_blocks(message.strip())
            passive_rag_blocks = list(rag_blocks or [])
            rag_section = format_rag_section(rag_blocks)
            if rag_section:
                llm_message = f"{rag_section}\n\n{llm_message}"
        except Exception:  # noqa: BLE001
            pass

    # 运行时 Playbook：按意图注入步骤规程（失败不阻断；不进 system prompt，避免打散 create_agent 缓存）
    playbook_ids: list[str] = []
    try:
        from app.services.playbook import format_playbook_section, match_playbooks

        matches = match_playbooks(message.strip(), recent_user_messages=prior)
        playbook_section = format_playbook_section(matches)
        if playbook_section:
            playbook_ids = [m.playbook.id for m in matches]
            # 与设备控制注记一致：保证有「使用者本轮消息」分段，便于历史回显剥离 Playbook
            if USER_TURN_SECTION_HEADER not in llm_message:
                llm_message = f"{USER_TURN_SECTION_HEADER}\n\n{message.strip()}"
            llm_message = f"{playbook_section}\n\n{llm_message}"
    except Exception:  # noqa: BLE001
        pass

    from contracts.agent_debug import agent_debug, preview_text

    agent_debug(
        "flow.context.assembled",
        thread_id=thread_id,
        raw_message=preview_text(message.strip(), max_len=120),
        llm_user_message=llm_message,
        current_path=str(meta.get("current_path") or ""),
        recent_user_messages=prior[-5:],
        skip_passive_rag=skip_passive_rag,
        playbook_ids=playbook_ids,
    )
    return AgentContext(
        thread_id=thread_id,
        message=message.strip(),
        llm_user_message=llm_message,
        metadata=meta,
        recent_user_messages=prior,
        passive_rag_blocks=tuple(passive_rag_blocks),
        skip_passive_rag=skip_passive_rag,
        playbook_ids=tuple(playbook_ids),
    )
