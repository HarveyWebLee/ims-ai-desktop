"""
从 LangGraph Checkpoint 还原前端可渲染的会话消息结构。

文件职责
--------
读出 Checkpoint 里的 LangChain Message，拼成侧栏用的
``[{role, blocks:[{type:text|tool_call|client_action,...}]}]``。

在 Agent 流程中的位置
--------------------
会话历史只读还原（不参与当轮推理）：
  GET /threads/{id}/messages
    → api.sessions.get_thread_state
    → get_thread_ui_messages → read_checkpoint_messages → checkpoint_messages_to_ui

如何被调用
----------
- 消息历史 API / 状态接口需要「可渲染气泡」时
- ``extract_user_texts``：从还原结果再抽近期用户原文（时间正序）

白话解释
--------
Checkpoint 里是「内部剧本」（Human/AI/Tool 交替）；本模块翻译成「聊天气泡」。
工具调用与其后的 ToolMessage 会绑成一块 tool_call，并尽量抽出 client_action
（如下载、跳转）被前端重放。

与 session_store 的区别:
    - session_store：仅存用户消息文本列表（轻量，供多轮上下文）
    - thread_history：从 Checkpoint 还原完整对话含工具调用结果

注意:
    Postgres 模式下 Checkpointer 为 AsyncPostgresSaver，读状态须 ``await aget``，
    不可在 FastAPI 主线程调用同步 ``get``。
"""

from __future__ import annotations

# ── 标准库 ──
import json
import logging
from typing import Any

# ── LangChain ──
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

# ── 项目内 ──
from app.persistence.bootstrap import get_checkpointer
from app.services.prompt_assembly import extract_user_display_message
from app.utils.runnable_config import thread_runnable_config

logger = logging.getLogger(__name__)


async def read_checkpoint_messages(thread_id: str) -> list[Any]:
    """
    读取 checkpoint 中的原始 LangChain 消息列表。

    参数:
        thread_id: 会话线程 ID（LangGraph configurable.thread_id）

    返回:
        Message 对象列表；失败或无数据时返回 []

    说明:
        持久化为 AsyncPostgresSaver 时，主线程必须走 aget，禁止同步 get
        （否则 InvalidStateError，会话历史会静默变空）。
    """
    config = thread_runnable_config(thread_id)
    try:
        checkpoint = await get_checkpointer().aget(config)
    except Exception:
        logger.exception("读取 checkpoint 失败: thread_id=%s", thread_id)
        return []
    if not checkpoint:
        return []
    channel_values = checkpoint.get("channel_values") or {}
    return list(channel_values.get("messages") or [])


def _text_content(content: Any) -> str:
    """
    将 LangChain message content 统一为字符串。

    content 可能是 str、list（多模态块）、None 等格式。

    参数:
        content: message.content 原始值

    返回:
        纯文本字符串
    """
    if isinstance(content, str):
        return content
    if content is None:
        return ""
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and part.get("type") == "text":
                parts.append(str(part.get("text", "")))
        return "".join(parts)
    return json.dumps(content, ensure_ascii=False)


def _parse_tool_result(result: str) -> dict[str, Any] | None:
    """
    解析 tool_result JSON 字符串。

    参数:
        result: ToolMessage.content 字符串

    返回:
        解析后的 dict，失败返回 None
    """
    try:
        data = json.loads(result)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError, TypeError:
        pass
    return None


def _client_actions_from_result(result: str) -> list[dict[str, Any]]:
    """
    从工具结果 JSON 中提取 client_action / client_actions（前端需执行的跳转、下载等）。

    参数:
        result: 工具返回 JSON 字符串

    返回:
        client_action dict 列表，无则空列表
    """
    parsed = _parse_tool_result(result)
    if not parsed:
        return []
    actions = parsed.get("client_actions")
    if isinstance(actions, list):
        return [item for item in actions if isinstance(item, dict)]
    action = parsed.get("client_action")
    return [action] if isinstance(action, dict) else []


def _client_action_from_result(result: str) -> dict[str, Any] | None:
    """兼容旧调用：返回首个 client_action。"""
    actions = _client_actions_from_result(result)
    return actions[0] if actions else None


def checkpoint_messages_to_ui(messages: list[Any]) -> list[dict[str, Any]]:
    """
    将 checkpoint 消息序列转为前端 blocks 结构。

    输出格式:
        [{ role: "user"|"assistant", mid?: str, blocks: [{type, ...}] }]

    参数:
        messages: LangChain Message 列表

    返回:
        UI 消息列表

    说明:
        自最近一条 HumanMessage 起的 assistant 气泡共享该 Human 的 mid（方案 B 多卡同 mid）。
    """
    ui: list[dict[str, Any]] = []
    i = 0
    current_mid: str | None = None
    # while 手动控制索引，因为 AIMessage+ToolMessage 需成组处理
    while i < len(messages):
        msg = messages[i]

        if isinstance(msg, HumanMessage):
            text = extract_user_display_message(_text_content(msg.content)).strip()
            kwargs = getattr(msg, "additional_kwargs", None) or {}
            current_mid = (
                str(kwargs["mid"]).strip()
                if kwargs.get("mid")
                else (str(msg.id).strip() if getattr(msg, "id", None) else None)
            ) or None
            if text:
                entry: dict[str, Any] = {
                    "role": "user",
                    "blocks": [{"type": "text", "content": text}],
                }
                if current_mid:
                    entry["mid"] = current_mid
                ui.append(entry)
            i += 1
            continue

        if isinstance(msg, AIMessage):
            blocks: list[dict[str, Any]] = []
            text = _text_content(msg.content).strip()
            if text:
                blocks.append({"type": "text", "content": text})

            tool_calls = list(msg.tool_calls or [])
            if tool_calls:
                # 收集紧随其后的 ToolMessage（LangGraph 约定顺序）
                tool_results: dict[str, str] = {}
                j = i + 1
                while j < len(messages) and isinstance(messages[j], ToolMessage):
                    tm = messages[j]
                    tool_results[tm.tool_call_id] = _text_content(tm.content)
                    j += 1

                for tc in tool_calls:
                    tc_id = tc.get("id") or ""
                    tool_name = tc.get("name") or "unknown"
                    args = tc.get("args") if isinstance(tc.get("args"), dict) else {}
                    result = tool_results.get(tc_id, "")
                    tool_block: dict[str, Any] = {
                        "type": "tool_call",
                        "tool": tool_name,
                        "args": args,
                        "status": "done",
                        "result": result,
                    }
                    if tc_id:
                        tool_block["tool_call_id"] = tc_id
                    blocks.append(tool_block)
                    for client_action in _client_actions_from_result(result):
                        blocks.append(
                            {
                                "type": "client_action",
                                "action": client_action,
                                "status": "done",
                            }
                        )
                i = j  # 跳过已处理的 ToolMessage
            else:
                i += 1

            if blocks:
                entry = {"role": "assistant", "blocks": blocks}
                if current_mid:
                    entry["mid"] = current_mid
                ui.append(entry)
            continue

        # 孤立的 ToolMessage（无对应 AIMessage）跳过
        i += 1

    return ui


def attach_pending_interrupt_to_ui(
    ui_messages: list[dict[str, Any]],
    pending: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """
    将 checkpoint pending HITL 挂到对应助手气泡（按 mid；无 mid 则挂最后一条助手）。

    历史还原与实时流一致：有 pending 时 UI 必有 interrupt 块可交互。
    """
    if not pending or not isinstance(pending, dict):
        return ui_messages

    mid = str(pending.get("mid") or "").strip() or None
    result = [dict(item) for item in ui_messages]
    target_idx: int | None = None

    if mid:
        for i in range(len(result) - 1, -1, -1):
            item = result[i]
            if item.get("role") == "assistant" and str(item.get("mid") or "") == mid:
                target_idx = i
                break

    if target_idx is None:
        for i in range(len(result) - 1, -1, -1):
            if result[i].get("role") == "assistant":
                target_idx = i
                break

    interrupt_block = {"type": "interrupt", "payload": pending}
    if target_idx is None:
        entry: dict[str, Any] = {
            "role": "assistant",
            "blocks": [interrupt_block],
        }
        if mid:
            entry["mid"] = mid
        result.append(entry)
        return result

    blocks = [
        b
        for b in (result[target_idx].get("blocks") or [])
        if not (isinstance(b, dict) and b.get("type") == "interrupt")
    ]
    blocks.append(interrupt_block)
    updated = {**result[target_idx], "blocks": blocks}
    if mid and not updated.get("mid"):
        updated["mid"] = mid
    result[target_idx] = updated
    return result


async def get_thread_ui_messages(thread_id: str) -> list[dict[str, Any]]:
    """
    对外入口：thread_id → UI 消息列表。

    参数:
        thread_id: 会话 ID

    返回:
        前端 blocks 结构消息列表；无 checkpoint 时 []
    """
    raw = await read_checkpoint_messages(thread_id)
    if not raw:
        return []
    return checkpoint_messages_to_ui(raw)


async def extract_user_texts(thread_id: str, *, limit: int = 4) -> list[str]:
    """
    从 checkpoint 提取近期用户文本（供多轮时间上下文 / prompt 拼接）。

    参数:
        thread_id: 会话 ID
        limit: 最多返回几条

    返回:
        用户消息文本列表（时间正序）
    """
    texts: list[str] = []
    for item in await get_thread_ui_messages(thread_id):
        if item.get("role") != "user":
            continue
        for block in item.get("blocks") or []:
            if block.get("type") == "text" and block.get("content"):
                texts.append(str(block["content"]))
    return texts[-limit:]  # 取最后 limit 条
