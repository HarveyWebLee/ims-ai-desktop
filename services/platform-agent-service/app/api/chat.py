"""
SSE 流式对话 API 模块

文件职责
--------
提供 `POST /api/agent/chat` 的核心处理逻辑：
校验参数 → 维护会话索引 → 调用 LangGraph `stream_chat` → 将图事件流转换为 SSE（Server-Sent Events）推送给前端。

在 Agent 流程中的位置
--------------------
这是 Agent **主入口**：
  前端 AiAssistant 发送用户消息
    → chat_sse()
    → stream_chat()（LangGraph 图：Plan → Tools → LLM → HITL interrupt 等）
    → SSE 事件：token、tool_start、tool_end、plan、interrupt、client_action 等
  若图在 HITL 处中断，前端展示确认/补参表单，用户提交后走 resume.py 而非再次 chat。

如何被调用
----------
- 路由：`app/main.py` 中 `@app.post("/api/agent/chat")` → `chat.chat_sse(request, body)`
- 请求体：JSON，结构见 `ChatRequest`
- 响应：`text/event-stream`，非 JSON envelope（错误时 SSE 内 event:error 或 HTTP 400 JSON）

SSE 格式说明
------------
每条消息形如：
  event: <事件名>
  data: <JSON 字符串>

空行分隔多条 event（`_format_sse` 负责格式化）。
"""

# ---------------------------------------------------------------------------
# 标准库：延迟注解求值，便于前向引用与 3.10+ 联合类型 str | None
# ---------------------------------------------------------------------------
from __future__ import annotations

# ---------------------------------------------------------------------------
# 标准库：JSON 序列化 SSE data 行
# ---------------------------------------------------------------------------
import asyncio
import json

# ---------------------------------------------------------------------------
# 标准库：Any 表示任意类型；用于 metadata、payload 等动态结构
# ---------------------------------------------------------------------------
from collections.abc import AsyncIterable, AsyncIterator
from typing import Any

# ---------------------------------------------------------------------------
# 第三方：FastAPI 请求对象与响应类型
# ---------------------------------------------------------------------------
from fastapi import Request
from fastapi.responses import JSONResponse, StreamingResponse

# ---------------------------------------------------------------------------
# 第三方：Pydantic 请求体验证；Field(...) 表示必填并附加校验规则
# ---------------------------------------------------------------------------
from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# 本项目：失败时 JSON 响应体
# ---------------------------------------------------------------------------
from app.api.response import fail

# ---------------------------------------------------------------------------
# 本项目：LangGraph 流式对话入口（异步生成器）
# ---------------------------------------------------------------------------
from app.application.conversation.chat import stream_chat

# ---------------------------------------------------------------------------
# 本项目：从 Authorization 解析 user_id
# ---------------------------------------------------------------------------
from app.middleware.auth import get_current_user_id

# ---------------------------------------------------------------------------
# 本项目：模型目录校验与默认 model_id
# ---------------------------------------------------------------------------
from app.models.catalog import get_catalog_item, get_default_model_id

# ---------------------------------------------------------------------------
# 本项目：会话元数据与用户消息缓存（多轮上下文、侧栏列表）
# ---------------------------------------------------------------------------
from app.services.session_store import session_store
from contracts.context import normalize_run_mode


class ChatRequest(BaseModel):
    """
    POST /api/agent/chat 的请求体模型。

    Pydantic BaseModel 会在 FastAPI 入参绑定时自动校验类型与 Field 约束，
    校验失败时 FastAPI 返回 422，不会进入 chat_sse 函数体。

    字段
    ----
    thread_id : str
        会话唯一 ID，前端生成 UUID，贯穿 checkpoint 与 SSE 重连。
    mid : str | None
        用户本轮需求 ID；省略时后端生成。SSE / resume / 历史投影按 mid 归属。
    message : str
        用户本轮输入文本，min_length=1 禁止空字符串。
    model_id : str | None
        选用的 LLM；省略时后端使用 catalog 默认模型。
    metadata : dict | None
        可选上下文，如当前页面路径、选中设备等，注入 Agent state。
    recent_user_messages : list[str] | None
        前端维护的近期用户句列，供「直达告警查询」等短路路径做意图理解
        （不依赖 LangGraph checkpoint 的场景）。
    run_mode : str | None
        会话运行模式：readonly | confirm | autonomous；缺省 confirm。
    plan_first : bool
        显式「先计划后执行」：覆盖 AI-first，多步任务走 plan_confirm。
    """

    thread_id: str = Field(..., min_length=1)
    mid: str | None = None
    message: str = Field(..., min_length=1)
    model_id: str | None = None
    metadata: dict[str, Any] | None = None
    # 前端传入的近期用户消息，注入 LLM 上下文供多轮意图理解
    recent_user_messages: list[str] | None = None
    run_mode: str | None = None
    plan_first: bool = False

    @field_validator("run_mode", mode="before")
    @classmethod
    def _normalize_run_mode(cls, value: Any) -> str:
        return normalize_run_mode(str(value) if value is not None else None)


def _client_actions_from_tool_result(result_data: dict[str, Any]) -> list[dict[str, Any]]:
    """从 tool_result JSON 提取需前端执行的 client_action（支持分批导出）。"""
    actions = result_data.get("client_actions")
    if isinstance(actions, list):
        return [item for item in actions if isinstance(item, dict)]
    action = result_data.get("client_action")
    return [action] if isinstance(action, dict) else []


def _format_sse(event: str, data: dict[str, Any]) -> str:
    """
    将事件名与数据字典格式化为 SSE 协议规定的一段文本。

    参数
    ----
    event : str
        SSE 事件类型名，前端 addEventListener 或按行解析 event: 字段。
    data : dict
        将序列化为单行 JSON（ensure_ascii=False 保留中文）。

    返回
    ----
    str
        以双换行结尾的 SSE 片段，可直接 yield 给 StreamingResponse。
    """
    # f-string 多行：event 行 + data 行 + 空行分隔
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _payload_with_mid(payload: dict[str, Any]) -> dict[str, Any]:
    """为 SSE payload 注入本轮 mid（已有则不覆盖）。"""
    from contracts.context import current_message_id

    mid = (current_message_id.get() or "").strip()
    if not mid or payload.get("mid"):
        return payload
    return {**payload, "mid": mid}


# HITL 前平台 API（如统计 6 万条告警）可能耗时 30s+，需周期性 SSE 注释保活
_SSE_KEEPALIVE_INTERVAL_SEC = 8.0


def _is_client_disconnect(exc: BaseException) -> bool:
    """客户端/代理断开连接时不应误报为「模型服务调用失败」。"""
    import asyncio

    if isinstance(exc, asyncio.CancelledError):
        return True
    name = type(exc).__name__
    if name in (
        "BrokenResourceError",
        "BrokenPipeError",
        "ConnectionResetError",
        "ConnectionAbortedError",
        "EndOfStream",
    ):
        return True
    msg = str(exc).lower()
    return any(
        k in msg for k in ("disconnect", "connection reset", "broken pipe", "closed connection")
    )


async def _iter_sse_with_keepalive(
    event_stream: AsyncIterable[tuple[str, dict[str, Any]]],
) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    """
    带周期性注释保活的 SSE 事件迭代。

    LangGraph 工具节点（如 export 统计总数）可能阻塞数十秒才产出 interrupt，
    若长时间无字节下发，浏览器/开发代理会断开连接并触发误报 error SSE。

    注意：禁止使用 asyncio.wait_for(agen.__anext__())——超时后会 cancel 内层
    生成器，导致 tool_start 已下发但 tool_end 永远到不了前端（连接被静默掐断）。
    改为挂起同一 __anext__ Task，超时仅 emit keepalive 注释，不取消内层迭代。
    """
    agen = event_stream.__aiter__()
    pending: asyncio.Task[tuple[str, dict[str, Any]]] | None = None
    while True:
        if pending is None:
            pending = asyncio.ensure_future(agen.__anext__())
        next_task = pending

        done, _ = await asyncio.wait(
            {next_task},
            timeout=_SSE_KEEPALIVE_INTERVAL_SEC,
            return_when=asyncio.FIRST_COMPLETED,
        )

        if next_task in done:
            try:
                item = next_task.result()
            except StopAsyncIteration:
                break
            pending = None
            yield item
        else:
            yield ("__keepalive__", {})


def _clear_thread_orchestration_on_abort(thread_id: str | None, *, reason: str) -> None:
    """
    abort / 客户端断开时尽力清理编排暂存，避免侧栏仍显示旧 Plan / HITL。

    checkpoint interrupt 仍交给下一轮 chat 的 abandon；此处仅清 BPMN / execution_state。
    """
    tid = (thread_id or "").strip()
    if not tid:
        return
    try:
        from app.services.session_store import clear_thread_orchestration
        from contracts.agent_debug import agent_debug, orchestration_snapshot

        before = orchestration_snapshot(tid)
        clear_thread_orchestration(tid)
        try:
            from app.services.bpmn_observability import record_hitl_lifecycle

            record_hitl_lifecycle(
                action="abort",
                interrupt_type=reason,
                thread_id=tid,
            )
        except Exception:
            pass
        agent_debug(
            "flow.sse.abort_clear_orchestration",
            thread_id=tid,
            reason=reason,
            before=before,
            after=orchestration_snapshot(tid),
        )
    except Exception as exc:
        from contracts.agent_debug import agent_debug

        agent_debug(
            "flow.sse.abort_clear_orchestration_failed",
            thread_id=tid,
            reason=reason,
            exc_type=type(exc).__name__,
            detail=str(exc)[:160],
        )


async def _sse_from_stream(
    event_stream: AsyncIterable[tuple[str, dict[str, Any]]],
    *,
    thread_id: str | None = None,
) -> StreamingResponse:
    """
    将 conversation 应用用例产出的异步事件流包装为 FastAPI StreamingResponse。

    参数
    ----
    event_stream : AsyncIterator[tuple[str, dict]]
        `stream_chat` / `stream_resume` 返回的 async for 可迭代对象，
        每次迭代为 (event_name, payload) 二元组。
    thread_id : str | None
        会话 ID；abort / 断开时用于清理编排 pending。

    返回
    ----
    StreamingResponse
        media_type 为 text/event-stream，浏览器/EventSource 可持续读取。

    异常
    ----
    流内未捕获异常会转为 SSE event:error 推给前端，避免连接静默断开。
    """

    # 内部异步生成器：StreamingResponse 消费此生成器逐 chunk 写回 HTTP
    async def event_generator():
        yield ": keepalive\n\n"
        try:
            async for event_name, payload in _iter_sse_with_keepalive(event_stream):
                if event_name == "__keepalive__":
                    yield ": keepalive\n\n"
                    continue

                from contracts.agent_debug import trace_sse_outgoing

                out_payload = _payload_with_mid(payload) if isinstance(payload, dict) else payload
                trace_sse_outgoing(event_name, out_payload if isinstance(out_payload, dict) else {})
                if (
                    event_name == "tool_end"
                    and isinstance(out_payload, dict)
                    and out_payload.get("result")
                ):
                    try:
                        result_data = json.loads(out_payload["result"])
                        for action in _client_actions_from_tool_result(result_data):
                            yield _format_sse(
                                "client_action",
                                _payload_with_mid(action) if isinstance(action, dict) else action,
                            )
                    except json.JSONDecodeError, TypeError:
                        pass
                yield _format_sse(event_name, out_payload if isinstance(out_payload, dict) else {})
        except asyncio.CancelledError:
            _clear_thread_orchestration_on_abort(thread_id, reason="cancelled")
            raise
        except Exception as exc:
            if _is_client_disconnect(exc):
                from contracts.agent_debug import agent_debug

                agent_debug(
                    "flow.sse.client_disconnect",
                    exc_type=type(exc).__name__,
                    detail=str(exc)[:160],
                )
                _clear_thread_orchestration_on_abort(thread_id, reason="client_disconnect")
                raise
            from app.services.llm_error_mapper import format_llm_error_event
            from contracts.agent_debug import agent_debug

            agent_debug(
                "flow.sse.generator_error",
                exc_type=type(exc).__name__,
                detail=str(exc)[:200],
            )
            yield _format_sse(
                "error",
                format_llm_error_event(exc, code=50002, fallback_message="Agent 执行失败"),
            )

    return StreamingResponse(
        event_generator(),  # 传入生成器函数调用结果（生成器对象）
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",  # 禁止中间缓存 SSE
            "Connection": "keep-alive",  # 保持长连接
            "X-Accel-Buffering": "no",  # 禁止 Nginx 缓冲，保证实时推送
        },
    )


async def chat_sse(request: Request, body: ChatRequest):
    """
    处理一次用户对话请求并返回 SSE 流。

    参数
    ----
    request : Request
        FastAPI 原始请求，用于读取 Authorization 等 Header。
    body : ChatRequest
        已由 Pydantic 校验的 JSON 请求体。

    返回
    ----
    JSONResponse | StreamingResponse
        参数/模型错误 → HTTP 400 + fail envelope JSON
        成功 → SSE StreamingResponse

    业务流程
    --------
    1. 校验 thread_id、model_id
    2. 解析 user_id，upsert 会话标题，追加用户消息到 session_store
    3. 调用 stream_chat 并转为 SSE
    """
    if not body.thread_id.strip():
        return JSONResponse(fail(40002, "参数错误", "thread_id 不能为空"), status_code=400)

    # 空 model_id 用 catalog 默认；or 短路求值
    model_id = body.model_id or get_default_model_id()
    if not get_catalog_item(model_id):
        return JSONResponse(
            fail(40001, "参数错误", "model_id 不在模型目录中或已禁用"),
            status_code=400,
        )

    authorization = request.headers.get("authorization")
    user_id = await get_current_user_id(authorization)
    # 会话标题取消息前 20 字，超长加省略号
    title = body.message[:20] + ("…" if len(body.message) > 20 else "")
    session_store.upsert_session(user_id, body.thread_id, title)
    # 记录用户消息（直达告警查询不写 LangGraph checkpoint，靠此做多轮上下文）
    session_store.append_user_message(body.thread_id, body.message)

    from contracts.agent_debug import agent_debug, preview_text

    agent_debug(
        "flow.api.chat",
        thread_id=body.thread_id,
        mid=(body.mid or "").strip() or None,
        model_id=model_id,
        message_preview=preview_text(body.message, max_len=120),
        current_path=str((body.metadata or {}).get("current_path") or ""),
        recent_user_messages=(body.recent_user_messages or [])[-3:],
    )

    # await _sse_from_stream：等待包装完成并返回 StreamingResponse
    return await _sse_from_stream(
        stream_chat(
            thread_id=body.thread_id,
            model_id=model_id,
            message=body.message,
            metadata=body.metadata,
            auth_token=authorization,
            recent_user_messages=body.recent_user_messages,
            user_id=user_id,
            mid=body.mid,
            run_mode=body.run_mode,
            plan_first=body.plan_first,
        ),
        thread_id=body.thread_id,
    )
