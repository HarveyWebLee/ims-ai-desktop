"""
LangGraph Checkpoint 辅助工具

文件职责
--------
围绕「会话状态快照」（checkpoint）做读、修、清：
- 判断图是否仍停在 HITL interrupt 等待 resume
- 从 checkpoint 补发 interrupt SSE（流标志滞后时）
- 新消息前静默拒绝 stale interrupt / 修复未闭合的 tool_calls
- SSE error 时写入助手错误文案（历史可恢复）
- 排查用消息摘要、消息条数、恢复上次工具参数

在 Agent 流程中的位置
--------------------
  stream_chat（新意图）
    → abandon_stale_checkpoint_interrupt / repair_dangling_tool_calls
  stream_resume / run_agent_stream 空闲超时
    → collect_pending_interrupt_payloads / agent_has_pending_interrupt
  ReAct 重试
    → recover_last_tool_call_args

如何被调用
----------
- `application.conversation.stream_chat_core` / `stream_resume_core`
- `stream_parent_graph` / `agent_stream_adapter`（checkpoint 补发 interrupt）

关键概念（白话）
----------------
- Checkpoint：按 thread_id 存的「图进行到哪了 + messages」。
- Interrupt：工具或节点喊停等人确认；不解则下一轮可能卡住。
- dangling tool_calls：模型说了要调工具，但 ToolMessage 没写上
  （常见于 SSE 提前断开）→ LLM 下一轮会收到非法消息序列。
- Command(resume=reject)：用「用户拒绝」静默把图从 interrupt 里拉出来。
"""

# ---------------------------------------------------------------------------
# 标准库
# ---------------------------------------------------------------------------
from __future__ import annotations

import json
import logging
from typing import Any

from app.utils.runnable_config import thread_runnable_config

logger = logging.getLogger(__name__)

# 未完成 tool_calls 的占位 ToolMessage 摘要（供 LLM 与前端解析 user_cancelled）
_DANGLING_TOOL_CANCEL_JSON = json.dumps(
    {
        "ok": False,
        "summary": "上次工具调用未完成，已自动取消",
        "user_cancelled": True,
    },
    ensure_ascii=False,
)


async def _aget_parent_snap(thread_id: str, model_id: str) -> Any | None:
    """异步读取父图 StateSnapshot（配合 AsyncPostgresSaver）。"""
    tid = (thread_id or "").strip()
    if not tid:
        return None
    try:
        from app.graph.agent_factory import get_parent_graph

        agent = get_parent_graph(model_id)
        config = thread_runnable_config(tid)
        return await agent.aget_state(config)
    except Exception:
        logger.debug("agent aget_state 失败: thread=%s", tid, exc_info=True)
        return None


def _snap_has_interrupt(snap: Any) -> bool:
    if snap is None:
        return False
    tasks = getattr(snap, "tasks", None) or ()
    for task in tasks:
        if getattr(task, "interrupts", None):
            return True
    values = getattr(snap, "values", None) or {}
    return bool(isinstance(values, dict) and values.get("__interrupt__"))


async def parent_has_pending_interrupt(thread_id: str, model_id: str) -> bool:
    """检查父图 checkpoint 是否仍有待 resume 的 interrupt。"""
    return await agent_has_pending_interrupt(thread_id, model_id)


async def agent_has_pending_interrupt(thread_id: str, model_id: str) -> bool:
    """检查父图 checkpoint 是否仍有待 resume 的 interrupt。"""
    snap = await _aget_parent_snap(thread_id, model_id)
    return _snap_has_interrupt(snap)


async def collect_pending_interrupt_payloads(thread_id: str, model_id: str) -> list[dict[str, Any]]:
    """从 checkpoint 读取图内待 resume 的 interrupt 载荷。"""
    tid = (thread_id or "").strip()
    if not tid:
        return []
    snap = await _aget_parent_snap(tid, model_id)
    if not _snap_has_interrupt(snap):
        return []

    payloads: list[dict[str, Any]] = []
    tasks = getattr(snap, "tasks", None) or ()
    for task in tasks:
        interrupts = getattr(task, "interrupts", None) or ()
        for intr in interrupts:
            value = intr.value if hasattr(intr, "value") else intr
            if isinstance(value, dict):
                payloads.append(value)

    values = getattr(snap, "values", None) or {}
    if isinstance(values, dict):
        raw = values.get("__interrupt__")
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    payloads.append(item)

    return payloads


def _mid_from_checkpoint_messages(messages: list[Any]) -> str | None:
    """从 checkpoint 最近一条 HumanMessage 解析 mid。"""
    from langchain_core.messages import HumanMessage

    for msg in reversed(messages):
        if not isinstance(msg, HumanMessage):
            continue
        kwargs = getattr(msg, "additional_kwargs", None) or {}
        found = kwargs.get("mid") or getattr(msg, "id", None)
        if found:
            return str(found).strip() or None
    return None


def enrich_interrupt_payload_mid(
    payload: dict[str, Any],
    *,
    messages: list[Any] | None = None,
    fallback_mid: str | None = None,
) -> dict[str, Any]:
    """为 interrupt 载荷补 mid（已有则不覆盖）。"""
    if not isinstance(payload, dict):
        return payload
    if str(payload.get("mid") or "").strip():
        return payload
    mid = (fallback_mid or "").strip() or None
    if not mid and messages:
        mid = _mid_from_checkpoint_messages(messages)
    if not mid:
        return payload
    return {**payload, "mid": mid}


async def get_pending_interrupt_for_thread(
    thread_id: str,
    *,
    model_id: str | None = None,
) -> dict[str, Any] | None:
    """
    读取会话当前待处理 HITL（供 /state 与历史恢复）。

    返回首个 dict 载荷，并尽量附带 mid（来自最近 HumanMessage）。
    """
    from app.models.catalog import get_default_model_id
    from app.services.thread_history import read_checkpoint_messages

    tid = (thread_id or "").strip()
    if not tid:
        return None
    mid_model = (model_id or "").strip() or get_default_model_id()
    payloads = await collect_pending_interrupt_payloads(tid, mid_model)
    if not payloads:
        return None
    raw_messages = await read_checkpoint_messages(tid)
    return enrich_interrupt_payload_mid(payloads[0], messages=raw_messages)


async def abandon_stale_checkpoint_interrupt(
    thread_id: str,
    model_id: str,
) -> bool:
    """
    静默 Command(resume=reject) 清除图内 stale interrupt。

    用于:
        - 用户点击取消后，不向前端透传 plan/tool SSE，仅清理 checkpoint
        - 新一轮 chat 开始前，丢弃上一轮未完成的图内 HITL

    参数:
        thread_id / model_id: 目标会话与模型

    返回:
        True 表示 interrupt 已清除或原本不存在；
        False 表示尝试后仍检测到 pending interrupt。

    副作用:
        会驱动一次 `run_agent_stream`（reject resume），可能推进图状态；
        错误仅记 debug，不向外抛。
    """
    tid = (thread_id or "").strip()
    if not tid or not await agent_has_pending_interrupt(tid, model_id):
        return True

    from langgraph.types import Command

    from app.graph.parent_graph_stream import stream_parent_graph
    from contracts.agent_debug import agent_debug
    from contracts.context import (
        current_auth_token,
        current_hitl_reject_drain,
        safe_reset_contextvar,
    )

    agent_debug("checkpoint.abandon_start", thread_id=tid)
    reject_payload = {"type": "reject", "approved": False}
    # 显式透传当前 JWT，避免 stream_parent_graph 在调用方未传 auth 时误清 ContextVar
    inherited_auth = current_auth_token.get()
    # 拒绝后禁止 Agent 再调 MCP（取消结果返回后 LLM 可能重试写工具）
    drain_token = current_hitl_reject_drain.set(True)
    try:
        async for event_name, payload in stream_parent_graph(
            thread_id=tid,
            model_id=model_id,
            input_payload=Command(resume=reject_payload),
            auth_token=inherited_auth,
        ):
            if event_name == "error":
                agent_debug(
                    "checkpoint.abandon_error_event",
                    thread_id=tid,
                    detail=str((payload or {}).get("message", ""))[:120],
                )
                break
    except Exception as exc:
        agent_debug(
            "checkpoint.abandon_exception",
            thread_id=tid,
            error=str(exc)[:120],
        )
    finally:
        safe_reset_contextvar(
            current_hitl_reject_drain,
            drain_token,
            label="current_hitl_reject_drain",
        )

    cleared = not await agent_has_pending_interrupt(tid, model_id)
    agent_debug("checkpoint.abandon_done", thread_id=tid, cleared=cleared)
    return cleared


async def checkpoint_messages_summary(
    thread_id: str,
    model_id: str,
    *,
    tail: int = 10,
) -> list[dict[str, Any]]:
    """读取父图 checkpoint 最近消息摘要（供排查）。"""
    tid = (thread_id or "").strip()
    if not tid:
        return []
    try:
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

        from app.services.prompt_assembly import extract_user_display_message
        from contracts.agent_debug import preview_text, summarize_tool_result

        snap = await _aget_parent_snap(tid, model_id)
    except Exception:
        return [{"error": "get_state_failed"}]

    if snap is None:
        return []

    values = getattr(snap, "values", None) or {}
    messages = values.get("messages") if isinstance(values, dict) else None
    if not isinstance(messages, list):
        return []

    pending_interrupt = _snap_has_interrupt(snap)
    summary: list[dict[str, Any]] = []
    for msg in messages[-tail:]:
        entry: dict[str, Any] = {"cls": type(msg).__name__}
        if isinstance(msg, HumanMessage):
            raw = msg.content if isinstance(msg.content, str) else str(msg.content)
            entry["role"] = "user"
            # 展示层去掉路径注入等内部包装
            entry["content_preview"] = preview_text(
                extract_user_display_message(raw),
                max_len=200,
            )
        elif isinstance(msg, AIMessage):
            entry["role"] = "assistant"
            content = msg.content
            if isinstance(content, str) and content.strip():
                entry["content_preview"] = preview_text(content, max_len=200)
            if msg.tool_calls:
                entry["tool_calls"] = [
                    {
                        "name": str(tc.get("name") or ""),
                        "args": tc.get("args") if isinstance(tc.get("args"), dict) else {},
                    }
                    for tc in msg.tool_calls
                    if isinstance(tc, dict)
                ]
        elif isinstance(msg, ToolMessage):
            entry["role"] = "tool"
            entry["tool"] = str(msg.name or "")
            raw = msg.content if isinstance(msg.content, str) else str(msg.content)
            entry["result_summary"] = summarize_tool_result(raw)
        elif isinstance(msg, SystemMessage):
            entry["role"] = "system"
            entry["content_preview"] = preview_text(
                msg.content if isinstance(msg.content, str) else str(msg.content),
                max_len=120,
            )
        else:
            entry["role"] = getattr(msg, "type", "unknown")
        summary.append(entry)

    if pending_interrupt:
        summary.append({"checkpoint_pending_interrupt": True})
    return summary


async def persist_run_error_message(
    thread_id: str,
    model_id: str,
    error_payload: dict[str, Any] | None,
    *,
    mid: str | None = None,
) -> bool:
    """
    将本轮 SSE error 写入 checkpoint 助手消息，供历史会话可恢复。

    官方路径：父图 ``aupdate_state`` + ``add_messages`` 追加 ``AIMessage``
    （与 ``repair_dangling_tool_calls`` 同源）。不引入图外消息表。

    返回:
        True 表示已写入或已存在等价文案；False 表示跳过/失败。
    """
    tid = (thread_id or "").strip()
    mid_id = (model_id or "").strip()
    if not tid or not mid_id:
        return False

    from app.services.llm_error_mapper import format_error_assistant_content
    from contracts.agent_debug import agent_debug

    content = format_error_assistant_content(
        error_payload if isinstance(error_payload, dict) else None
    )
    if not content.strip():
        return False

    try:
        from langchain_core.messages import AIMessage, HumanMessage

        from app.graph.agent_factory import get_parent_graph

        agent = get_parent_graph(mid_id)
        config = thread_runnable_config(tid)
        snap = await agent.aget_state(config)
    except Exception:
        logger.debug(
            "persist_run_error_message aget_state 失败: thread=%s",
            tid,
            exc_info=True,
        )
        return False

    values = getattr(snap, "values", None) or {} if snap is not None else {}
    messages = values.get("messages") if isinstance(values, dict) else None
    if not isinstance(messages, list):
        messages = []

    # 同 turn 已有等价错误文案则幂等跳过（避免 chat/resume 重复 error 双写）
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            break
        if isinstance(msg, AIMessage):
            existing = str(getattr(msg, "content", "") or "")
            if content in existing or (
                existing.lstrip().startswith("⚠️")
                and str((error_payload or {}).get("message") or "") in existing
            ):
                agent_debug(
                    "checkpoint.persist_run_error_skip_dup",
                    thread_id=tid,
                    mid=(mid or "").strip() or None,
                )
                return True
            break

    ai_kwargs: dict[str, Any] = {}
    turn_mid = (mid or "").strip()
    if turn_mid:
        ai_kwargs["additional_kwargs"] = {"mid": turn_mid}

    to_append: list[Any] = []
    if not messages:
        # 图未落盘用户句时（极早失败），从 session_store 补一条，避免历史只有错误助手卡
        try:
            from app.services.session_store import get_user_messages

            recent = get_user_messages(tid, limit=1)
            if recent:
                human_kwargs: dict[str, Any] = {}
                if turn_mid:
                    human_kwargs["id"] = turn_mid
                    human_kwargs["additional_kwargs"] = {"mid": turn_mid}
                to_append.append(HumanMessage(content=str(recent[-1]), **human_kwargs))
        except Exception:
            logger.debug(
                "persist_run_error_message 读取 session_store 失败: thread=%s",
                tid,
                exc_info=True,
            )

    to_append.append(AIMessage(content=content, **ai_kwargs))

    try:
        await agent.aupdate_state(
            config,
            {"messages": to_append},
        )
        agent_debug(
            "checkpoint.persist_run_error",
            thread_id=tid,
            mid=turn_mid or None,
            content_preview=content[:120],
            appended=len(to_append),
        )
        return True
    except Exception:
        logger.warning(
            "persist_run_error_message aupdate_state 失败: thread=%s",
            tid,
            exc_info=True,
        )
        return False


async def repair_dangling_tool_calls(thread_id: str, model_id: str) -> int:
    """为 checkpoint 中未闭合的 AIMessage.tool_calls 补写取消 ToolMessage。"""
    tid = (thread_id or "").strip()
    if not tid:
        return 0
    try:
        from langchain_core.messages import AIMessage, ToolMessage

        from app.graph.agent_factory import get_parent_graph
        from contracts.agent_debug import agent_debug

        agent = get_parent_graph(model_id)
        config = thread_runnable_config(tid)
        snap = await agent.aget_state(config)
    except Exception:
        logger.debug("repair_dangling_tool_calls aget_state 失败: thread=%s", tid, exc_info=True)
        return 0

    if snap is None:
        return 0

    values = getattr(snap, "values", None) or {}
    messages = values.get("messages") if isinstance(values, dict) else None
    if not isinstance(messages, list) or not messages:
        return 0

    # 已应答的 tool_call_id（含后续任意位置的 ToolMessage）
    answered_ids: set[str] = set()
    for msg in messages:
        if isinstance(msg, ToolMessage) and msg.tool_call_id:
            answered_ids.add(str(msg.tool_call_id))

    repairs: list[ToolMessage] = []
    for msg in messages:
        if not isinstance(msg, AIMessage) or not msg.tool_calls:
            continue
        for tc in msg.tool_calls:
            if not isinstance(tc, dict):
                continue
            tc_id = tc.get("id")
            if not tc_id or str(tc_id) in answered_ids:
                continue
            tc_id_str = str(tc_id)
            repairs.append(
                ToolMessage(
                    content=_DANGLING_TOOL_CANCEL_JSON,
                    tool_call_id=tc_id_str,
                    name=str(tc.get("name") or ""),
                )
            )
            answered_ids.add(tc_id_str)

    if not repairs:
        return 0

    try:
        await agent.aupdate_state(config, {"messages": repairs})
        agent_debug(
            "checkpoint.repair_dangling_tool_calls",
            thread_id=tid,
            repaired_count=len(repairs),
            tools=[str(m.name or "") for m in repairs],
        )
    except Exception:
        logger.warning(
            "repair_dangling_tool_calls aupdate_state 失败: thread=%s",
            tid,
            exc_info=True,
        )
        return 0

    return len(repairs)


async def checkpoint_message_count(thread_id: str, model_id: str) -> int:
    """读取父图 checkpoint 当前 messages 条数。"""
    tid = (thread_id or "").strip()
    if not tid:
        return 0
    try:
        snap = await _aget_parent_snap(tid, model_id)
    except Exception:
        return 0
    if snap is None:
        return 0
    values = getattr(snap, "values", None) or {}
    messages = values.get("messages") if isinstance(values, dict) else None
    return len(messages) if isinstance(messages, list) else 0


async def recover_last_tool_call_args(
    thread_id: str,
    model_id: str,
    tool_name: str,
) -> dict[str, Any]:
    """从 checkpoint 逆序查找指定工具最近一次 AIMessage.tool_calls 参数。"""
    tid = (thread_id or "").strip()
    name = (tool_name or "").strip()
    if not tid or not name:
        return {}
    try:
        from langchain_core.messages import AIMessage

        snap = await _aget_parent_snap(tid, model_id)
    except Exception:
        logger.debug(
            "recover_last_tool_call_args aget_state 失败: thread=%s tool=%s",
            tid,
            name,
            exc_info=True,
        )
        return {}

    if snap is None:
        return {}

    values = getattr(snap, "values", None) or {}
    messages = values.get("messages") if isinstance(values, dict) else None
    if not isinstance(messages, list):
        return {}

    for msg in reversed(messages):
        if not isinstance(msg, AIMessage) or not msg.tool_calls:
            continue
        for tc in msg.tool_calls:
            if not isinstance(tc, dict):
                continue
            if str(tc.get("name") or "") != name:
                continue
            args = dict(tc.get("args") or {})
            if args:
                return args
    return {}
