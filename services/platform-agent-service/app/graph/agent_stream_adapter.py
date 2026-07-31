"""
Agent astream_events(v3) → SSE 事件适配层

把 LangGraph 流投影翻译为前端 SSE 元组：
  message / tool_start / tool_end / interrupt

父图路径统一走 ``iter_agent_sse_events(_async)``：
  - 有 ``tool_calls`` 投影 → create_agent 快路径
  - 否则 → StateGraph values 增量 + 可选 ``custom``（须挂 CustomTransformer）

官方（docs-langchain event-streaming）：v3 默认无 CustomTransformer；
``get_stream_writer`` 自定义数据须显式 transformers。双路径保留，勿强行合并。

调用链：
  stream_parent_graph → iter_agent_sse_events_async → stream_envelope → chat/resume SSE
"""

# ---------------------------------------------------------------------------
# 标准库
# ---------------------------------------------------------------------------
from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator, Iterator
from typing import Any

# ---------------------------------------------------------------------------
# 第三方：从 values 增量识别工具调用与结果
# ---------------------------------------------------------------------------
from langchain_core.messages import AIMessage, ToolMessage

# ---------------------------------------------------------------------------
# 本项目
# ---------------------------------------------------------------------------
from app.application.execution.common import _tool_output_to_str, emit_tool_events
from contracts.agent_debug import (
    agent_debug,
    preview_text,
    summarize_tool_args,
    summarize_tool_result,
)

logger = logging.getLogger(__name__)

# 门控内 FlowIr JSON 误入聊天气泡：内容特征（nostream 在 astream_events v3 上偶发失效）
_FLOW_IR_MARKERS = ('"conditions"', '"nodes"', '"entry"')
_FLOW_IR_DECIDE_MAX = 120


def _is_flow_ir_leak_text(text: str) -> bool:
    """整段文本是否为内部 FlowIr JSON（不应作为助手回复展示）。"""
    s = (text or "").strip()
    if not s or s[0] != "{":
        return False
    return all(m in s for m in _FLOW_IR_MARKERS)


class _FlowIrTokenGate:
    """
    对流式 token 做短缓冲：若确认为 FlowIr JSON 则整段丢弃。

    官方推荐 nostream + disable_streaming；此处为 SSE 兜底，防止门控 IR 泄漏。
    """

    def __init__(self) -> None:
        self._buf = ""
        self._hold: list[str] = []
        self._mode = "unknown"  # unknown | pass | suppress

    def feed(self, token: str) -> list[str]:
        if not token:
            return []
        if self._mode == "pass":
            return [token]
        if self._mode == "suppress":
            return []

        self._buf += token
        self._hold.append(token)
        stripped = self._buf.lstrip()
        if not stripped:
            return []
        if stripped[0] not in "{[":
            return self._release_as_pass()
        if all(m in self._buf for m in _FLOW_IR_MARKERS):
            agent_debug(
                "flow.sse.suppress_flow_ir",
                preview=preview_text(self._buf, max_len=160),
            )
            self._mode = "suppress"
            self._hold.clear()
            return []
        # 缓冲过长仍无 FlowIr 特征 → 放行
        if len(self._buf) >= _FLOW_IR_DECIDE_MAX and '"conditions"' not in self._buf:
            return self._release_as_pass()
        return []

    def flush(self) -> list[str]:
        if self._mode == "suppress":
            return []
        if self._mode == "unknown" and _is_flow_ir_leak_text(self._buf):
            agent_debug(
                "flow.sse.suppress_flow_ir",
                preview=preview_text(self._buf, max_len=160),
            )
            self._mode = "suppress"
            self._hold.clear()
            return []
        return self._release_as_pass()

    def _release_as_pass(self) -> list[str]:
        self._mode = "pass"
        out = list(self._hold)
        self._hold.clear()
        return out


def _iter_gated_message_tokens(tokens: Any) -> Iterator[str]:
    """对单次 LLM 消息流应用 FlowIr 门闸。"""
    gate = _FlowIrTokenGate()
    for token in tokens:
        if not token:
            continue
        yield from gate.feed(str(token))
    yield from gate.flush()


async def _aiter_gated_message_tokens(tokens: Any) -> AsyncIterator[str]:
    """异步版 FlowIr 门闸。"""
    gate = _FlowIrTokenGate()
    async for token in tokens:
        if not token:
            continue
        for out in gate.feed(str(token)):
            yield out
    for out in gate.flush():
        yield out


def supports_tool_calls_projection(stream: Any) -> bool:
    """
    判断 stream_events v3 是否提供 create_agent 专用的 `tool_calls` 投影。

    有则走「投影直出」快路径；无则走 StateGraph 的 values 增量解析。
    """
    extensions = getattr(stream, "extensions", None)
    if not extensions:
        return False
    return "tool_calls" in extensions


def _wait_tool_call_finished(stream: Any, tool_stream: Any) -> None:
    """
    ToolCallStream 在 tool-started 时 output 可能仍为空，需 pump 至 finished。

    无 `_pump_next` 时静默返回（测试桩或不支持的 stream）。
    """
    pump = getattr(stream, "_pump_next", None)
    if pump is None:
        return
    while not getattr(tool_stream, "completed", True):
        if not pump():
            break


def _stream_is_interrupted(stream: Any) -> bool:
    """
    安全读取 interrupt 标志（不用会卡住的 @property）。

    禁止访问 GraphRunStream.interrupted @property：该属性会先 `_drive_until_done`
    跑完全图，阻塞 asyncio / 工作线程，导致 tool_start SSE 无法及时下发。
    """
    if hasattr(stream, "_interrupted"):
        return bool(stream._interrupted)
    # 单测 FakeStream 等桩对象（类属性 interrupted=True）
    if "interrupted" in getattr(stream, "__dict__", {}):
        return bool(stream.__dict__["interrupted"])
    cls_val = getattr(type(stream), "interrupted", None)
    if isinstance(cls_val, bool):
        return cls_val
    return False


def _stream_interrupt_list(stream: Any) -> list[Any]:
    """读取 interrupt 载荷列表（不触发全量 pump）。"""
    if hasattr(stream, "_interrupts"):
        return list(stream._interrupts or [])
    if "interrupts" in getattr(stream, "__dict__", {}):
        return list(stream.__dict__["interrupts"] or [])
    cls_val = getattr(type(stream), "interrupts", None)
    if isinstance(cls_val, list):
        return list(cls_val)
    return []


def _pump_stream_step(stream: Any) -> bool:
    """驱动 v3 stream 前进一步；无 pump 接口时返回 False。"""
    pump = getattr(stream, "_pump_next", None)
    if pump is None:
        return False
    return bool(pump())


def _pump_until_interrupted(stream: Any, *, max_steps: int = 5000) -> None:
    """HITL 兜底 pump，直至 interrupt 或图步进结束。"""
    for _ in range(max_steps):
        if _stream_is_interrupted(stream):
            return
        if not _pump_stream_step(stream):
            return


async def _apump_stream_step(stream: Any) -> bool:
    """异步 v3 stream 单步 pump；无 _apump_next 时回退同步 _pump_next。"""
    apump = getattr(stream, "_apump_next", None)
    if apump is not None:
        return bool(await apump())
    return _pump_stream_step(stream)


async def _apump_until_interrupted(stream: Any, *, max_steps: int = 5000) -> None:
    """异步 HITL 兜底 pump。"""
    for _ in range(max_steps):
        if _stream_is_interrupted(stream):
            return
        if not await _apump_stream_step(stream):
            return


async def _apump_until_tool_call_answered(
    stream: Any,
    *,
    tool_call_id: str,
    max_steps: int = 5000,
) -> str:
    """tool_start 后异步增量 pump（对齐 _pump_until_tool_call_answered）。"""
    if not tool_call_id:
        return "stopped"
    if getattr(stream, "_apump_next", None) is None and getattr(stream, "_pump_next", None) is None:
        return "no_pump"
    for _ in range(max_steps):
        if _tool_call_answered(_stream_latest_messages(stream), tool_call_id):
            return "answered"
        if _stream_is_interrupted(stream) or _stream_interrupt_list(stream):
            return "interrupted"
        if not await _apump_stream_step(stream):
            if _tool_call_answered(_stream_latest_messages(stream), tool_call_id):
                return "answered"
            if _stream_is_interrupted(stream) or _stream_interrupt_list(stream):
                return "interrupted"
            return "stopped"
    if _tool_call_answered(_stream_latest_messages(stream), tool_call_id):
        return "answered"
    if _stream_is_interrupted(stream) or _stream_interrupt_list(stream):
        return "interrupted"
    agent_debug(
        "flow.ai.pump_tool_timeout",
        tool_call_id=tool_call_id[:24],
    )
    return "timeout"


async def _aiter_message_text_tokens(message_item: Any) -> AsyncIterator[str]:
    """
    异步消费 messages 投影的 text token。

    官方 v3：``async for token in message.text``；亦可 ``await message.text`` 取全文。
    同步 FakeStream 桩仍可能返回可同步迭代的 text，此处兼容。
    经 FlowIr 门闸，避免门控 IR JSON 泄漏到 SSE。
    """
    text = getattr(message_item, "text", None)
    if text is None:
        return

    async def _raw() -> AsyncIterator[str]:
        if hasattr(text, "__aiter__"):
            async for token in text:
                if token:
                    yield str(token)
            return
        if hasattr(text, "__await__"):
            full = await text
            if full:
                yield str(full)
            return
        for token in text:
            if token:
                yield str(token)

    async for out in _aiter_gated_message_tokens(_raw()):
        yield out


async def _async_interleave(stream: Any, *names: str) -> AsyncIterator[tuple[str, Any]]:
    """
    AsyncGraphRunStream 多投影按到达序合并（官方 v3 异步路径无 sync interleave）。

    逻辑对齐 langgraph GraphRunStream.interleave，pump 使用 _apump_next。
    """
    from langgraph.stream.stream_channel import StreamChannel

    extensions = getattr(stream, "extensions", None) or {}
    channels: dict[str, StreamChannel[Any]] = {}
    try:
        for name in names:
            ch = extensions[name]
            if not isinstance(ch, StreamChannel):
                raise TypeError(
                    f"interleave() requires StreamChannel projections, "
                    f"got {type(ch).__name__} for {name!r}"
                )
            if ch._subscribed:
                raise RuntimeError(
                    f"StreamChannel {name!r} already has a subscriber; use .atee(n) for fan-out."
                )
            ch._subscribed = True
            channels[name] = ch

        done: set[str] = set()
        while len(done) < len(channels):
            best: tuple[int, str] | None = None
            for name, ch in channels.items():
                if name in done:
                    continue
                if ch._closed and not ch._items:
                    if ch._error is not None:
                        raise ch._error
                    done.add(name)
                    continue
                if ch._items:
                    stamp = ch._items[0][0]
                    if best is None or stamp < best[0]:
                        best = (stamp, name)

            if best is not None:
                _stamp, item = channels[best[1]]._items.popleft()
                yield (best[1], item)
            else:
                if not await _apump_stream_step(stream):
                    before = len(done)
                    for name, ch in channels.items():
                        if name not in done and not ch._items:
                            if ch._closed:
                                if ch._error is not None:
                                    raise ch._error
                                done.add(name)
                    if len(done) == before:
                        break
    finally:
        for ch in channels.values():
            ch._subscribed = False


def _stream_latest_messages(stream: Any) -> list[Any]:
    """读取 GraphRunStream 最新 values.messages（不触发全量 pump）。"""
    latest = getattr(stream, "_latest", None)
    if isinstance(latest, dict):
        messages = latest.get("messages")
        if isinstance(messages, list):
            return messages
    return []


def _tool_call_answered(messages: list[Any], tool_call_id: str) -> bool:
    """指定 tool_call_id 是否已有 ToolMessage 应答。"""
    if not tool_call_id:
        return False
    for msg in messages:
        if isinstance(msg, ToolMessage) and str(msg.tool_call_id or "") == tool_call_id:
            return True
    return False


def _pump_until_tool_call_answered(
    stream: Any,
    *,
    tool_call_id: str,
    max_steps: int = 5000,
) -> str:
    """
    tool_start 后增量 pump，直至 ToolMessage 落盘、HITL interrupt 或泵停止。

    返回:
        answered | interrupted | stopped | timeout | no_pump（无 _pump_next，走 interleave）
    """
    if not tool_call_id:
        return "stopped"
    if getattr(stream, "_pump_next", None) is None:
        return "no_pump"
    for _ in range(max_steps):
        # 本工具已有 ToolMessage 时优先 answered，避免后续工具 HITL 抢先判 interrupted
        # 导致本工具 tool_end 丢失、Plan 误把成功步标为 skipped
        if _tool_call_answered(_stream_latest_messages(stream), tool_call_id):
            return "answered"
        if _stream_is_interrupted(stream) or _stream_interrupt_list(stream):
            return "interrupted"
        if not _pump_stream_step(stream):
            if _tool_call_answered(_stream_latest_messages(stream), tool_call_id):
                return "answered"
            if _stream_is_interrupted(stream) or _stream_interrupt_list(stream):
                return "interrupted"
            # 同步 ToolNode 可能在本次 pump 内执行完工具后才返回 False
            return "stopped"
    if _tool_call_answered(_stream_latest_messages(stream), tool_call_id):
        return "answered"
    if _stream_is_interrupted(stream) or _stream_interrupt_list(stream):
        return "interrupted"
    agent_debug(
        "flow.ai.pump_tool_timeout",
        tool_call_id=tool_call_id[:24],
    )
    return "timeout"


def _interrupt_signature(payload: dict[str, Any]) -> str:
    """同轮 HITL 去重键（type + tool + message 摘要）。"""
    return json.dumps(
        {
            "type": payload.get("type"),
            "tool": payload.get("tool"),
            "message": str(payload.get("message") or "")[:500],
        },
        sort_keys=True,
        ensure_ascii=False,
    )


def _yield_interrupt_events(
    stream: Any,
    *,
    emitted: set[str] | None = None,
) -> Iterator[tuple[str, dict[str, Any]]]:
    """图内 interrupt() 暂停时下发 interrupt SSE。"""
    if not _stream_is_interrupted(stream):
        return
    seen = emitted if emitted is not None else set()
    for intr in _stream_interrupt_list(stream):
        value = intr.value if hasattr(intr, "value") else intr
        if isinstance(value, dict):
            sig = _interrupt_signature(value)
            if sig in seen:
                continue
            seen.add(sig)
            agent_debug(
                "flow.ai.hitl_interrupt",
                interrupt_type=value.get("type"),
                tool=value.get("tool"),
                message_preview=preview_text(value.get("message"), max_len=160),
            )
            yield ("interrupt", value)
        else:
            payload = {"type": "ask_params", "message": str(value)}
            sig = _interrupt_signature(payload)
            if sig not in seen:
                seen.add(sig)
                yield ("interrupt", payload)


def iter_stream_interrupt_events(
    stream: Any,
) -> Iterator[tuple[str, dict[str, Any]]]:
    """安全读取流内部 interrupt 状态，避免访问会驱动整张图的公开属性。"""
    yield from _yield_interrupt_events(stream)


def _yield_interrupt_from_checkpoint(
    *,
    model_id: str = "",
    emitted: set[str] | None = None,
) -> Iterator[tuple[str, dict[str, Any]]]:
    """同步路径不再读 AsyncPostgresSaver；由 chat/resume / 异步适配器补发。"""
    _ = model_id, emitted
    return
    yield  # pragma: no cover


async def _ayield_interrupt_from_checkpoint(
    *,
    model_id: str = "",
    emitted: set[str] | None = None,
) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    """stream 标志未同步时，从 checkpoint 异步补发 interrupt SSE。"""
    from app.graph.checkpoint_utils import collect_pending_interrupt_payloads
    from contracts.context import current_thread_id

    tid = (current_thread_id.get() or "").strip()
    mid = (model_id or "").strip()
    if not tid or not mid:
        return
    seen = emitted if emitted is not None else set()
    for payload in await collect_pending_interrupt_payloads(tid, mid):
        sig = _interrupt_signature(payload)
        if sig in seen:
            continue
        seen.add(sig)
        agent_debug(
            "flow.ai.hitl_from_checkpoint",
            thread_id=tid,
            interrupt_type=payload.get("type"),
            tool=payload.get("tool"),
            message_preview=preview_text(payload.get("message"), max_len=160),
        )
        yield ("interrupt", payload)


def _yield_all_interrupts(
    stream: Any,
    *,
    model_id: str = "",
    emitted: set[str],
) -> Iterator[tuple[str, dict[str, Any]]]:
    """图内 interrupt 下发（checkpoint 兜底仅异步路径）。"""
    yield from _yield_interrupt_events(stream, emitted=emitted)
    yield from _yield_interrupt_from_checkpoint(model_id=model_id, emitted=emitted)


async def _ayield_all_interrupts(
    stream: Any,
    *,
    model_id: str = "",
    emitted: set[str],
) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    """异步：图内 interrupt + checkpoint 兜底。"""
    for evt in _yield_interrupt_events(stream, emitted=emitted):
        yield evt
    async for evt in _ayield_interrupt_from_checkpoint(model_id=model_id, emitted=emitted):
        yield evt


def _finalize_tool_call_stream(
    stream: Any,
    *,
    tool_call_id: str,
    tool_name: str,
    pump_status: str,
    emitted_tool_ends: set[str],
    model_id: str = "",
    emitted_interrupts: set[str] | None = None,
    open_tool_calls: dict[str, str] | None = None,
) -> Iterator[tuple[str, dict[str, Any]]]:
    """
    tool_start 后的统一收尾：仅补发 tool_end。

    interrupt 由调用方在 flush 同批 ToolMessage 之后统一下发，保证 tool_end 先于 interrupt。
    """
    del model_id, emitted_interrupts  # 保留签名兼容；interrupt 改由调用方下发
    if pump_status == "answered":
        yield from _yield_tool_end_from_latest(
            stream,
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            emitted_tool_ends=emitted_tool_ends,
            open_tool_calls=open_tool_calls,
        )
        return

    # pump 停止/超时/中断/无 pump：若本工具 ToolMessage 已落盘，仍先发 tool_end
    if pump_status in ("stopped", "timeout", "interrupted", "no_pump"):
        buffered: list[tuple[str, dict[str, Any]]] = []
        for evt in _yield_tool_end_from_latest(
            stream,
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            emitted_tool_ends=emitted_tool_ends,
            open_tool_calls=open_tool_calls,
        ):
            buffered.append(evt)
        if buffered:
            for evt in buffered:
                yield evt
        if pump_status in ("interrupted", "stopped", "timeout", "no_pump"):
            agent_debug(
                "flow.ai.tool_pump_paused",
                tool=tool_name,
                pump_status=pump_status,
            )


def _flush_pending_tool_ends(
    stream: Any,
    *,
    pending_messages: list[Any],
    emitted_tool_ends: set[str],
    open_tool_calls: dict[str, str] | None = None,
) -> Iterator[tuple[str, dict[str, Any]]]:
    """
    HITL 提前结束前补发 tool_end：同批 values 内 ToolMessage + _latest 兜底。

    图在单帧 values 内可能已写入 ToolMessage，但 AIMessage 处理因 interrupt 提前 return，
    导致 ToolMessage 分支未执行、Plan 仍显示 running。
    """
    for msg in pending_messages:
        if isinstance(msg, ToolMessage):
            yield from _yield_tool_end_for_message(
                msg,
                emitted_tool_ends=emitted_tool_ends,
                open_tool_calls=open_tool_calls,
            )
    for msg in _stream_latest_messages(stream):
        if not isinstance(msg, ToolMessage):
            continue
        key = _stable_tool_message_key(msg)
        if key in emitted_tool_ends:
            continue
        yield from _yield_tool_end_for_message(
            msg,
            emitted_tool_ends=emitted_tool_ends,
            open_tool_calls=open_tool_calls,
        )


def _stable_tool_message_key(msg: ToolMessage) -> str:
    """ToolMessage 去重键：禁止用 id(msg)，避免每帧新对象导致 tool_end 洪泛。"""
    tc_id = str(msg.tool_call_id or "").strip()
    if tc_id:
        return f"tc:{tc_id}"
    mid = getattr(msg, "id", None)
    if mid:
        return f"id:{mid}"
    name = str(msg.name or "")
    content = msg.content
    if not isinstance(content, str):
        content = _tool_output_to_str(content)
    return f"body:{name}:{str(content)[:240]}"


def _yield_tool_end_for_message(
    msg: ToolMessage,
    *,
    emitted_tool_ends: set[str],
    open_tool_calls: dict[str, str] | None = None,
) -> Iterator[tuple[str, dict[str, Any]]]:
    """从 ToolMessage 构造 tool_end SSE（须能闭合尚未结束的 tool_start）。"""
    key = _stable_tool_message_key(msg)
    if key in emitted_tool_ends:
        return

    tool_name = str(msg.name or "")
    matched_start: str | None = None
    if open_tool_calls is not None:
        raw_tc = str(msg.tool_call_id or "").strip()
        if raw_tc and raw_tc in open_tool_calls:
            matched_start = raw_tc
        elif tool_name:
            for tc_id, name in open_tool_calls.items():
                if name == tool_name:
                    matched_start = tc_id
                    break
        if matched_start is None:
            agent_debug(
                "flow.ai.skip_orphan_tool_end",
                tool=tool_name,
                key_preview=key[:120],
            )
            return
        open_tool_calls.pop(matched_start, None)
        end_key = f"tc:{matched_start}"
    else:
        end_key = key

    if end_key in emitted_tool_ends:
        return
    emitted_tool_ends.add(end_key)
    emitted_tool_ends.add(key)

    result = msg.content
    if not isinstance(result, str):
        result = _tool_output_to_str(result)
    agent_debug(
        "flow.ai.llm_tool_result",
        tool=tool_name,
        result_summary=summarize_tool_result(str(result)),
    )
    yield ("tool_end", {"tool": tool_name, "result": str(result)})


def _yield_tool_end_from_latest(
    stream: Any,
    *,
    tool_call_id: str,
    tool_name: str = "",
    emitted_tool_ends: set[str],
    open_tool_calls: dict[str, str] | None = None,
) -> Iterator[tuple[str, dict[str, Any]]]:
    """pump 完成后从 _latest 即时下发 tool_end。"""
    messages = _stream_latest_messages(stream)
    # 优先按 tool_call_id 精确匹配
    for msg in messages:
        if not isinstance(msg, ToolMessage):
            continue
        tc_id = str(msg.tool_call_id or "").strip()
        if tool_call_id and tc_id == tool_call_id:
            yield from _yield_tool_end_for_message(
                msg,
                emitted_tool_ends=emitted_tool_ends,
                open_tool_calls=open_tool_calls,
            )
            return

    # 回退：按工具名匹配仍 open 的调用
    if tool_name:
        for msg in messages:
            if not isinstance(msg, ToolMessage):
                continue
            if str(msg.name or "") != tool_name:
                continue
            key = _stable_tool_message_key(msg)
            if key in emitted_tool_ends:
                continue
            yield from _yield_tool_end_for_message(
                msg,
                emitted_tool_ends=emitted_tool_ends,
                open_tool_calls=open_tool_calls,
            )
            return


def _custom_sse_dedupe_key(payload: dict[str, Any]) -> str:
    """custom 投影 tool_start/tool_end 去重键（须区分 retry 轮次，避免 AC-08 重试事件被吞）。"""
    sse = str(payload.get("sse_event") or "")
    tool = str(payload.get("tool") or "")
    retry_tag = "1" if payload.get("retry") else "0"
    attempt = str(payload.get("attempt") if payload.get("attempt") is not None else "")
    if sse == "tool_end":
        return (
            f"custom:tool_end:{tool}:r{retry_tag}:a{attempt}:"
            f"{str(payload.get('result') or '')[:240]}"
        )
    if sse == "tool_start":
        args = payload.get("args") if isinstance(payload.get("args"), dict) else {}
        return (
            f"custom:tool_start:{tool}:r{retry_tag}:a{attempt}:"
            f"{json.dumps(args, sort_keys=True, ensure_ascii=False)[:240]}"
        )
    return f"custom:{sse}:{tool}:{json.dumps(payload, sort_keys=True, ensure_ascii=False)[:240]}"


def _message_id(msg: Any) -> str:
    """消息去重键：优先用 LangChain id，否则类型名+稳定内容摘要（禁止 id(msg)）。"""
    mid = getattr(msg, "id", None)
    if mid:
        return str(mid)
    if isinstance(msg, ToolMessage):
        return _stable_tool_message_key(msg)
    content = getattr(msg, "content", "")
    if not isinstance(content, str):
        content = str(content)[:120]
    return f"{type(msg).__name__}:{content[:120]}"


def _ai_message_text(msg: AIMessage) -> str:
    """从 AIMessage 提取纯文本（兼容 str / content blocks）。"""
    content = msg.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text") or ""))
            else:
                text = getattr(block, "text", None)
                if text:
                    parts.append(str(text))
        return "".join(parts)
    return str(content or "")


def _tool_call_as_dict(tool_call: dict[str, Any] | Any) -> dict[str, Any]:
    """将 LangChain ToolCall / dict 统一为 dict。"""
    if isinstance(tool_call, dict):
        return tool_call
    return {
        "id": getattr(tool_call, "id", None),
        "name": getattr(tool_call, "name", None),
        "args": getattr(tool_call, "args", None) or {},
    }


def _tool_call_id(tool_call: dict[str, Any] | Any, *, fallback: str) -> str:
    """工具调用去重键：优先官方 id，否则 name+args 摘要。"""
    tc_dict = _tool_call_as_dict(tool_call)
    tc_id = tc_dict.get("id")
    if tc_id:
        return str(tc_id)
    name = str(tc_dict.get("name") or "")
    args = tc_dict.get("args") or {}
    return f"{fallback}:{name}:{json.dumps(args, sort_keys=True, ensure_ascii=False)}"


def iter_create_agent_sse_events(
    stream: Any, *, model_id: str = ""
) -> Iterator[tuple[str, dict[str, Any]]]:
    """
    create_agent 路径：interleave messages + tool_calls（原 B4）。

    产出文本 delta 与成对的 tool_start/tool_end；若工具途中 HITL，先发 tool_start 再 interrupt 并 return。
    收尾与 StateGraph 对齐：stream 标志滞后时从 checkpoint 补发 interrupt。
    """
    emitted_interrupts: set[str] = set()
    for kind, item in stream.interleave("messages", "tool_calls"):
        if kind == "messages":
            for token in _iter_gated_message_tokens(item.text):
                yield ("message", {"type": "text", "delta": token})
        elif kind == "tool_calls":
            _wait_tool_call_finished(stream, item)
            tool_name = item.tool_name
            tool_input = item.input or {}
            if _stream_is_interrupted(stream):
                yield ("tool_start", {"tool": tool_name, "args": tool_input})
                yield from _yield_all_interrupts(
                    stream,
                    model_id=model_id,
                    emitted=emitted_interrupts,
                )
                return
            if getattr(item, "error", None):
                result = json.dumps(
                    {"ok": False, "summary": str(item.error)},
                    ensure_ascii=False,
                )
            else:
                result = _tool_output_to_str(item.output)
            yield from emit_tool_events(tool_name, tool_input, result)

    yield from _yield_all_interrupts(
        stream,
        model_id=model_id,
        emitted=emitted_interrupts,
    )


def iter_state_graph_sse_events(
    stream: Any, *, model_id: str = ""
) -> Iterator[tuple[str, dict[str, Any]]]:
    """
    StateGraph：interleave messages + values（+ custom），从消息增量推导 tool 事件。

    values 中 AIMessage.tool_calls → tool_start；ToolMessage → tool_end。
    messages 投影 → 文本 token 流。
    custom 投影 → ``__custom__``（plan_execute 的 get_stream_writer SSE）。
    """
    seen_messages: set[str] = set()
    emitted_tool_starts: set[str] = set()
    emitted_tool_ends: set[str] = set()
    emitted_interrupts: set[str] = set()
    open_tool_calls: dict[str, str] = {}
    emitted_custom_keys: set[str] = set()
    # 父图 messages 投影通常不含 create_agent 子图 token；有则优先生效，避免 values 回填重复
    streamed_message_tokens = False
    from contracts.context import current_stream_message_skip

    skip = max(0, int(current_stream_message_skip.get() or 0))
    message_count = skip
    if skip > 0:
        agent_debug("flow.ai.stream_skip_history", skip_messages=skip)

    projections = ["messages", "values"]
    if "custom" in getattr(stream, "extensions", {}):
        projections.append("custom")

    for kind, item in stream.interleave(*projections):
        if kind == "messages":
            for token in _iter_gated_message_tokens(item.text):
                streamed_message_tokens = True
                yield ("message", {"type": "text", "delta": token})
            continue

        if kind == "custom":
            payload = item if isinstance(item, dict) else {}
            custom_key = _custom_sse_dedupe_key(payload)
            if custom_key in emitted_custom_keys:
                continue
            emitted_custom_keys.add(custom_key)
            sse = str(payload.get("sse_event") or "")
            tool = str(payload.get("tool") or "")
            if sse == "tool_start" and tool and tool not in open_tool_calls.values():
                open_tool_calls[f"custom:{tool}:{len(open_tool_calls)}"] = tool
            elif sse == "tool_end" and tool:
                for tc_id, name in list(open_tool_calls.items()):
                    if name == tool:
                        open_tool_calls.pop(tc_id, None)
                        break
            yield ("__custom__", payload)
            continue

        if kind != "values" or not isinstance(item, dict):
            continue

        messages = item.get("messages") or []
        if len(messages) < message_count:
            # 仅回拨游标；禁止清空 tool 去重（否则会出现大量重复 tool_end）
            message_count = len(messages)

        new_messages = messages[message_count:]
        message_count = len(messages)

        for msg in new_messages:
            msg_key = _message_id(msg)
            if msg_key in seen_messages:
                continue
            seen_messages.add(msg_key)

            if isinstance(msg, AIMessage) and msg.tool_calls:
                for tc in msg.tool_calls:
                    tc_dict = _tool_call_as_dict(tc)
                    tc_id = _tool_call_id(tc_dict, fallback=msg_key)
                    if tc_id in emitted_tool_starts:
                        continue
                    emitted_tool_starts.add(tc_id)
                    tool_name = str(tc_dict.get("name") or "")
                    tool_input = dict(tc_dict.get("args") or {})
                    open_tool_calls[tc_id] = tool_name
                    agent_debug(
                        "flow.ai.llm_tool_call",
                        tool=tool_name,
                        tool_args=summarize_tool_args(tool_input),
                    )
                    yield ("tool_start", {"tool": tool_name, "args": tool_input})
                    pump_status = _pump_until_tool_call_answered(
                        stream,
                        tool_call_id=tc_id,
                    )
                    if pump_status == "no_pump":
                        tool_end_emitted = False
                        for evt in _finalize_tool_call_stream(
                            stream,
                            tool_call_id=tc_id,
                            tool_name=tool_name,
                            pump_status=pump_status,
                            emitted_tool_ends=emitted_tool_ends,
                            model_id=model_id,
                            emitted_interrupts=emitted_interrupts,
                            open_tool_calls=open_tool_calls,
                        ):
                            if evt[0] == "tool_end":
                                tool_end_emitted = True
                            yield evt
                        if _stream_is_interrupted(stream) or _stream_interrupt_list(stream):
                            if not tool_end_emitted:
                                _pump_until_interrupted(stream)
                            yield from _flush_pending_tool_ends(
                                stream,
                                pending_messages=new_messages,
                                emitted_tool_ends=emitted_tool_ends,
                                open_tool_calls=open_tool_calls,
                            )
                            yield from _yield_all_interrupts(
                                stream,
                                model_id=model_id,
                                emitted=emitted_interrupts,
                            )
                            return
                    else:
                        tool_end_emitted = False
                        for evt in _finalize_tool_call_stream(
                            stream,
                            tool_call_id=tc_id,
                            tool_name=tool_name,
                            pump_status=pump_status,
                            emitted_tool_ends=emitted_tool_ends,
                            model_id=model_id,
                            emitted_interrupts=emitted_interrupts,
                            open_tool_calls=open_tool_calls,
                        ):
                            if evt[0] == "tool_end":
                                tool_end_emitted = True
                            yield evt
                        # HITL 中断或工具未完成时提前结束；补 pump 确保 interrupt SSE 不丢失
                        if pump_status == "interrupted" or (
                            pump_status not in ("answered",) and not tool_end_emitted
                        ):
                            _pump_until_interrupted(stream)
                            yield from _flush_pending_tool_ends(
                                stream,
                                pending_messages=new_messages,
                                emitted_tool_ends=emitted_tool_ends,
                                open_tool_calls=open_tool_calls,
                            )
                            yield from _yield_all_interrupts(
                                stream,
                                model_id=model_id,
                                emitted=emitted_interrupts,
                            )
                            return

            elif isinstance(msg, AIMessage) and not streamed_message_tokens:
                # create_agent 子图 token 不在父 messages 投影时，从 values 回填全文
                text = _ai_message_text(msg)
                if text and not _is_flow_ir_leak_text(text):
                    yield ("message", {"type": "text", "delta": text})
                elif text and _is_flow_ir_leak_text(text):
                    agent_debug(
                        "flow.sse.suppress_flow_ir",
                        preview=preview_text(text, max_len=160),
                    )

            if isinstance(msg, ToolMessage):
                yield from _yield_tool_end_for_message(
                    msg,
                    emitted_tool_ends=emitted_tool_ends,
                    open_tool_calls=open_tool_calls,
                )

    # interleave 结束后兜底：图可能在最后一次 values 后才写入 interrupt 标志
    _pump_until_interrupted(stream)
    yield from _yield_all_interrupts(
        stream,
        model_id=model_id,
        emitted=emitted_interrupts,
    )


async def _async_iter_create_agent_sse_events(
    stream: Any, *, model_id: str = ""
) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    """create_agent 异步路径：messages + tool_calls。"""
    emitted_interrupts: set[str] = set()
    projections = ["messages", "tool_calls"]
    if "custom" in getattr(stream, "extensions", {}):
        projections.append("custom")

    async for kind, item in _async_interleave(stream, *projections):
        if kind == "messages":
            async for token in _aiter_message_text_tokens(item):
                yield ("message", {"type": "text", "delta": token})
        elif kind == "tool_calls":
            _wait_tool_call_finished(stream, item)
            tool_name = item.tool_name
            tool_input = item.input or {}
            if _stream_is_interrupted(stream):
                yield ("tool_start", {"tool": tool_name, "args": tool_input})
                async for evt in _ayield_all_interrupts(
                    stream,
                    model_id=model_id,
                    emitted=emitted_interrupts,
                ):
                    yield evt
                return
            if getattr(item, "error", None):
                result = json.dumps(
                    {"ok": False, "summary": str(item.error)},
                    ensure_ascii=False,
                )
            else:
                result = _tool_output_to_str(item.output)
            for evt in emit_tool_events(tool_name, tool_input, result):
                yield evt
        elif kind == "custom":
            payload = item if isinstance(item, dict) else {}
            yield ("__custom__", payload)

    async for evt in _ayield_all_interrupts(
        stream,
        model_id=model_id,
        emitted=emitted_interrupts,
    ):
        yield evt


async def _async_iter_state_graph_sse_events(
    stream: Any, *, model_id: str = ""
) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    """StateGraph 异步路径：messages + values（+ custom）增量解析。"""
    seen_messages: set[str] = set()
    emitted_tool_starts: set[str] = set()
    emitted_tool_ends: set[str] = set()
    emitted_interrupts: set[str] = set()
    open_tool_calls: dict[str, str] = {}
    emitted_custom_keys: set[str] = set()
    streamed_message_tokens = False
    from contracts.context import current_stream_message_skip

    skip = max(0, int(current_stream_message_skip.get() or 0))
    message_count = skip
    if skip > 0:
        agent_debug("flow.ai.stream_skip_history", skip_messages=skip)

    projections = ["messages", "values"]
    if "custom" in getattr(stream, "extensions", {}):
        projections.append("custom")

    async for kind, item in _async_interleave(stream, *projections):
        if kind == "messages":
            async for token in _aiter_message_text_tokens(item):
                streamed_message_tokens = True
                yield ("message", {"type": "text", "delta": token})
            continue

        if kind == "custom":
            payload = item if isinstance(item, dict) else {}
            custom_key = _custom_sse_dedupe_key(payload)
            if custom_key in emitted_custom_keys:
                continue
            emitted_custom_keys.add(custom_key)
            sse = str(payload.get("sse_event") or "")
            tool = str(payload.get("tool") or "")
            if sse == "tool_start" and tool and tool not in open_tool_calls.values():
                open_tool_calls[f"custom:{tool}:{len(open_tool_calls)}"] = tool
            elif sse == "tool_end" and tool:
                for tc_id, name in list(open_tool_calls.items()):
                    if name == tool:
                        open_tool_calls.pop(tc_id, None)
                        break
            yield ("__custom__", payload)
            continue

        if kind != "values" or not isinstance(item, dict):
            continue

        messages = item.get("messages") or []
        if len(messages) < message_count:
            # 仅回拨游标；禁止清空 tool 去重
            message_count = len(messages)

        new_messages = messages[message_count:]
        message_count = len(messages)

        for msg in new_messages:
            msg_key = _message_id(msg)
            if msg_key in seen_messages:
                continue
            seen_messages.add(msg_key)

            if isinstance(msg, AIMessage) and msg.tool_calls:
                for tc in msg.tool_calls:
                    tc_dict = _tool_call_as_dict(tc)
                    tc_id = _tool_call_id(tc_dict, fallback=msg_key)
                    if tc_id in emitted_tool_starts:
                        continue
                    emitted_tool_starts.add(tc_id)
                    tool_name = str(tc_dict.get("name") or "")
                    tool_input = dict(tc_dict.get("args") or {})
                    open_tool_calls[tc_id] = tool_name
                    agent_debug(
                        "flow.ai.llm_tool_call",
                        tool=tool_name,
                        tool_args=summarize_tool_args(tool_input),
                    )
                    yield ("tool_start", {"tool": tool_name, "args": tool_input})
                    pump_status = await _apump_until_tool_call_answered(
                        stream,
                        tool_call_id=tc_id,
                    )
                    if pump_status == "no_pump":
                        tool_end_emitted = False
                        for evt in _finalize_tool_call_stream(
                            stream,
                            tool_call_id=tc_id,
                            tool_name=tool_name,
                            pump_status=pump_status,
                            emitted_tool_ends=emitted_tool_ends,
                            model_id=model_id,
                            emitted_interrupts=emitted_interrupts,
                            open_tool_calls=open_tool_calls,
                        ):
                            if evt[0] == "tool_end":
                                tool_end_emitted = True
                            yield evt
                        if _stream_is_interrupted(stream) or _stream_interrupt_list(stream):
                            if not tool_end_emitted:
                                await _apump_until_interrupted(stream)
                            for evt in _flush_pending_tool_ends(
                                stream,
                                pending_messages=new_messages,
                                emitted_tool_ends=emitted_tool_ends,
                                open_tool_calls=open_tool_calls,
                            ):
                                yield evt
                            for evt in _yield_all_interrupts(
                                stream,
                                model_id=model_id,
                                emitted=emitted_interrupts,
                            ):
                                yield evt
                            return
                    else:
                        tool_end_emitted = False
                        for evt in _finalize_tool_call_stream(
                            stream,
                            tool_call_id=tc_id,
                            tool_name=tool_name,
                            pump_status=pump_status,
                            emitted_tool_ends=emitted_tool_ends,
                            model_id=model_id,
                            emitted_interrupts=emitted_interrupts,
                            open_tool_calls=open_tool_calls,
                        ):
                            if evt[0] == "tool_end":
                                tool_end_emitted = True
                            yield evt
                        if pump_status == "interrupted" or (
                            pump_status not in ("answered",) and not tool_end_emitted
                        ):
                            await _apump_until_interrupted(stream)
                            for evt in _flush_pending_tool_ends(
                                stream,
                                pending_messages=new_messages,
                                emitted_tool_ends=emitted_tool_ends,
                                open_tool_calls=open_tool_calls,
                            ):
                                yield evt
                            for evt in _yield_all_interrupts(
                                stream,
                                model_id=model_id,
                                emitted=emitted_interrupts,
                            ):
                                yield evt
                            return

            elif isinstance(msg, AIMessage) and not streamed_message_tokens:
                text = _ai_message_text(msg)
                if text and not _is_flow_ir_leak_text(text):
                    yield ("message", {"type": "text", "delta": text})
                elif text and _is_flow_ir_leak_text(text):
                    agent_debug(
                        "flow.sse.suppress_flow_ir",
                        preview=preview_text(text, max_len=160),
                    )

            if isinstance(msg, ToolMessage):
                for evt in _yield_tool_end_for_message(
                    msg,
                    emitted_tool_ends=emitted_tool_ends,
                    open_tool_calls=open_tool_calls,
                ):
                    yield evt

    await _apump_until_interrupted(stream)
    for evt in _yield_all_interrupts(
        stream,
        model_id=model_id,
        emitted=emitted_interrupts,
    ):
        yield evt


def iter_agent_sse_events(
    stream: Any, *, model_id: str = ""
) -> Iterator[tuple[str, dict[str, Any]]]:
    """
    公开入口：create_agent v3 流适配（零兼容：仅 create_agent 投影路径）。
    """
    yield from iter_create_agent_sse_events(stream, model_id=model_id)


async def iter_agent_sse_events_async(
    stream_awaitable: Any,
    *,
    model_id: str = "",
) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    """
    异步父图 ``astream_events(v3)`` 适配。

    AsyncGraphRunStream 无 sync ``interleave``：按投影走 ``_async_interleave``；
    父 StateGraph 用 messages+values，create_agent 子图用 messages+tool_calls。
    """
    stream = await stream_awaitable

    async with stream:
        if hasattr(stream, "interleave"):
            if supports_tool_calls_projection(stream):
                for evt in iter_create_agent_sse_events(stream, model_id=model_id):
                    yield evt
            else:
                for evt in iter_state_graph_sse_events(stream, model_id=model_id):
                    yield evt
            return

        if supports_tool_calls_projection(stream):
            async for evt in _async_iter_create_agent_sse_events(stream, model_id=model_id):
                yield evt
        else:
            async for evt in _async_iter_state_graph_sse_events(stream, model_id=model_id):
                yield evt
