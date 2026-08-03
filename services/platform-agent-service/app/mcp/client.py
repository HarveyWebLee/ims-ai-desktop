"""
Agent 侧 MCP Client：Platform MCP + 可选外部 MCP。

- list_tools 可缓存（TTL）；每次 invoke 经 AuthHeaderInterceptor 透传 JWT / HITL bypass
- 图路径包装 authorize；Plan/Pipeline 使用无二次 authorize 的包装
- Platform MCP 不可达时不回退 runtime 本机工具（零兼容）
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any, cast

from langchain_core.tools import BaseTool, StructuredTool
from langchain_mcp_adapters.interceptors import MCPToolCallRequest

from app.config import settings
from app.mcp.connections import build_mcp_connections

logger = logging.getLogger(__name__)

# 图绑定：含 authorize
_mcp_tools_cache: list[BaseTool] | None = None
_mcp_tools_cache_at: float = 0.0
# Plan/Pipeline：仅 HITL 还原，不再 authorize
_mcp_pipeline_tools_cache: list[BaseTool] | None = None
_mcp_pipeline_tools_cache_at: float = 0.0
_warmup_status: dict[str, Any] = {"done": False, "ok": False, "tool_count": 0, "error": None}


def _cache_ttl_seconds() -> float:
    return float(getattr(settings, "agent_mcp_cache_ttl_seconds", 300) or 300)


def _cache_fresh(loaded_at: float) -> bool:
    ttl = _cache_ttl_seconds()
    if ttl <= 0:
        return loaded_at > 0
    return loaded_at > 0 and (time.monotonic() - loaded_at) < ttl


class AuthHeaderInterceptor:
    """把当前请求的 JWT / thread_id / HITL bypass 注入 MCP HTTP 头。"""

    async def __call__(
        self,
        request: MCPToolCallRequest,
        handler: Callable[[MCPToolCallRequest], Awaitable[Any]],
    ) -> Any:
        from contracts.context import (
            current_auth_token,
            current_hitl_confirm_bypass,
            current_run_mode,
            current_thread_id,
        )

        headers = dict(request.headers or {})
        token = current_auth_token.get()
        if token:
            headers["Authorization"] = (
                token if str(token).lower().startswith("bearer ") else f"Bearer {token}"
            )
        thread_id = current_thread_id.get()
        if thread_id:
            headers["X-Thread-Id"] = str(thread_id)
        if current_hitl_confirm_bypass.get():
            headers["X-Hitl-Confirm-Bypass"] = "1"
        # 自主模式：MCP ask_user_confirm 跳过确认
        headers["X-Run-Mode"] = current_run_mode.get() or "confirm"
        return await handler(request.override(headers=headers or None))


class McpToolCallLoggingInterceptor:
    """记录 MCP 工具调用（名称 / server / 耗时）。"""

    async def __call__(
        self,
        request: MCPToolCallRequest,
        handler: Callable[[MCPToolCallRequest], Awaitable[Any]],
    ) -> Any:
        started = time.perf_counter()
        try:
            result = await handler(request)
            logger.info(
                "mcp.tool_ok name=%s server=%s elapsed_ms=%.1f",
                request.name,
                request.server_name,
                (time.perf_counter() - started) * 1000,
            )
            return result
        except Exception:
            logger.exception(
                "mcp.tool_fail name=%s server=%s elapsed_ms=%.1f",
                request.name,
                request.server_name,
                (time.perf_counter() - started) * 1000,
            )
            raise


def _extract_hitl_payload(text: str) -> dict[str, Any] | None:
    """从 MCP 工具返回文本中提取 hitl_required 载荷。"""
    try:
        data = json.loads(text)
    except json.JSONDecodeError, TypeError:
        return None
    if isinstance(data, dict) and data.get("hitl_required") and data.get("payload"):
        payload = data["payload"]
        if isinstance(payload, dict):
            return dict(payload)
    return None


def _cancelled_hitl_tool_result(tool_name: str) -> str:
    """用户拒绝 HITL 时返回给 LLM 的统一 ToolResult（顶层 user_cancelled，供历史/重试识别）。"""
    from contracts.result import tool_result

    return tool_result(
        ok=False,
        summary="已取消操作",
        data={"tool": tool_name},
        user_cancelled=True,
    )


def _resolve_mcp_hitl_text(
    text: str,
    *,
    tool_name: str,
    kwargs: dict[str, Any],
    invoke_again: Callable[[dict[str, Any]], str],
) -> str:
    """
    将 MCP ``hitl_required`` 还原为图内 ``interrupt()``；resume 后 merge + bypass 重调 MCP。

    支持 ask_params → confirm 嵌套一次；第三层仍走 interrupt（零兼容，无 session pending）。
    """
    payload = _extract_hitl_payload(text)
    if payload is None:
        return text

    from app.graph.hitl_interrupt import interrupt_or_raise
    from contracts.context import current_hitl_confirm_bypass
    from contracts.hitl import is_hitl_reject, merge_hitl_resume_args

    resume_value = interrupt_or_raise(payload)
    if is_hitl_reject(resume_value):
        return _cancelled_hitl_tool_result(tool_name)

    merged = merge_hitl_resume_args(resume_value, dict(kwargs))
    bypass_reset = current_hitl_confirm_bypass.set(True)
    try:
        text2 = invoke_again(merged)
        payload2 = _extract_hitl_payload(text2)
        if payload2 is None:
            return text2

        # 嵌套 HITL（如先补参再 confirm）
        resume2 = interrupt_or_raise(payload2)
        if is_hitl_reject(resume2):
            return _cancelled_hitl_tool_result(tool_name)
        merged2 = merge_hitl_resume_args(resume2, merged)
        text3 = invoke_again(merged2)
        payload3 = _extract_hitl_payload(text3)
        if payload3 is not None:
            resume3 = interrupt_or_raise(payload3)
            if is_hitl_reject(resume3):
                return _cancelled_hitl_tool_result(tool_name)
            merged3 = merge_hitl_resume_args(resume3, merged2)
            return invoke_again(merged3)
        return text3
    finally:
        from contracts.context import safe_reset_contextvar

        safe_reset_contextvar(
            current_hitl_confirm_bypass,
            bypass_reset,
            label="current_hitl_confirm_bypass",
        )


def _maybe_raise_hitl(
    text: str,
    *,
    tool_name: str = "",
    kwargs: dict[str, Any] | None = None,
    invoke_again: Callable[[dict[str, Any]], str] | None = None,
) -> str:
    """
    MCP 返回 hitl_required 时走图内 interrupt 还原（须在 LangGraph 节点/工具包装器内调用）。
    """
    if invoke_again is not None:
        return _resolve_mcp_hitl_text(
            text,
            tool_name=tool_name,
            kwargs=kwargs or {},
            invoke_again=invoke_again,
        )
    payload = _extract_hitl_payload(text)
    if payload is None:
        return text
    from app.graph.hitl_interrupt import interrupt_or_raise

    interrupt_or_raise(payload)
    return text


def _extract_tool_text(raw: Any) -> str:
    if isinstance(raw, str):
        return raw
    if isinstance(raw, list):
        parts: list[str] = []
        for item in raw:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("text"):
                parts.append(str(item["text"]))
            else:
                parts.append(str(item))
        return "".join(parts) if parts else str(raw)
    return str(raw)


def _ainvoke_tool_in_sync_context(tool: BaseTool, kwargs: dict[str, Any]) -> Any:
    """
    在同步上下文中调用仅有 coroutine 的 MCP StructuredTool。

    langchain-mcp-adapters 返回的工具通常无 sync ``func``，直接 ``.invoke()``
    会抛出 ``StructuredTool does not support sync invocation.``。
    """
    import asyncio
    import concurrent.futures

    async def _call() -> Any:
        return await tool.ainvoke(kwargs)

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_call())

    # 已有运行中的事件循环：在独立线程开新 loop，避免嵌套 await
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(lambda: asyncio.run(_call())).result(timeout=120)


def invoke_underlying_mcp_tool_sync(tool: BaseTool, kwargs: dict[str, Any]) -> Any:
    """优先 sync；底层仅支持 async 时桥接 ``ainvoke``。"""
    if getattr(tool, "func", None) is not None:
        return tool.invoke(kwargs)
    return _ainvoke_tool_in_sync_context(tool, kwargs)


def _wrap_mcp_tool(tool: BaseTool, *, authorize: bool) -> BaseTool:
    def _authorize_or_deny(kwargs: dict[str, Any]) -> str | None:
        if not authorize:
            return None
        from app.application.tool_execution import (
            authorize_tool_call,
            denied_tool_result,
        )

        decision = authorize_tool_call(tool.name, kwargs)
        if not decision.allowed:
            return denied_tool_result(tool.name, decision)
        return None

    def _deny_readonly_if_needed() -> str | None:
        from contracts.context import current_run_mode
        from contracts.result import tool_result
        from contracts.tool_catalog_loader import is_write_tool

        if current_run_mode.get() != "readonly":
            return None
        if not is_write_tool(tool.name):
            return None
        from app.services.tool_subset import deny_readonly_write_summary

        return tool_result(
            ok=False,
            summary=deny_readonly_write_summary(tool.name),
            data={
                "error_code": "run_mode_readonly",
                "tool": tool.name,
                "non_retryable": True,
            },
        )

    def _run(**kwargs: Any) -> str:
        from contracts.context import current_hitl_reject_drain

        if current_hitl_reject_drain.get():
            return _cancelled_hitl_tool_result(tool.name)
        args = dict(kwargs)
        denied = _authorize_or_deny(args)
        if denied is not None:
            return denied
        readonly_denied = _deny_readonly_if_needed()
        if readonly_denied is not None:
            return readonly_denied

        def _invoke(call_args: dict[str, Any]) -> str:
            return _extract_tool_text(invoke_underlying_mcp_tool_sync(tool, call_args))

        return _resolve_mcp_hitl_text(
            _invoke(args),
            tool_name=tool.name,
            kwargs=args,
            invoke_again=_invoke,
        )

    async def _arun(**kwargs: Any) -> str:
        from contracts.context import current_hitl_reject_drain

        if current_hitl_reject_drain.get():
            return _cancelled_hitl_tool_result(tool.name)
        args = dict(kwargs)
        denied = _authorize_or_deny(args)
        if denied is not None:
            return denied
        readonly_denied = _deny_readonly_if_needed()
        if readonly_denied is not None:
            return readonly_denied

        async def _ainvoke(call_args: dict[str, Any]) -> str:
            return _extract_tool_text(await tool.ainvoke(call_args))

        text = await _ainvoke(args)
        payload = _extract_hitl_payload(text)
        if payload is None:
            return text

        # 异步路径：与 sync 相同的 HITL 还原；重调经线程安全桥接会丢失 contextvar，
        # 故在同协程内完成 interrupt + bypass 重调。
        from app.graph.hitl_interrupt import interrupt_or_raise
        from contracts.context import (
            current_hitl_confirm_bypass,
            safe_reset_contextvar,
        )
        from contracts.hitl import is_hitl_reject, merge_hitl_resume_args

        resume_value = interrupt_or_raise(payload)
        if is_hitl_reject(resume_value):
            return _cancelled_hitl_tool_result(tool.name)

        merged = merge_hitl_resume_args(resume_value, args)
        bypass_reset = current_hitl_confirm_bypass.set(True)
        try:
            text2 = await _ainvoke(merged)
            payload2 = _extract_hitl_payload(text2)
            if payload2 is None:
                return text2
            resume2 = interrupt_or_raise(payload2)
            if is_hitl_reject(resume2):
                return _cancelled_hitl_tool_result(tool.name)
            merged2 = merge_hitl_resume_args(resume2, merged)
            text3 = await _ainvoke(merged2)
            payload3 = _extract_hitl_payload(text3)
            if payload3 is not None:
                resume3 = interrupt_or_raise(payload3)
                if is_hitl_reject(resume3):
                    return _cancelled_hitl_tool_result(tool.name)
                merged3 = merge_hitl_resume_args(resume3, merged2)
                return await _ainvoke(merged3)
            return text3
        finally:
            safe_reset_contextvar(
                current_hitl_confirm_bypass,
                bypass_reset,
                label="current_hitl_confirm_bypass",
            )

    return StructuredTool.from_function(
        func=_run,
        coroutine=_arun,
        name=tool.name,
        description=tool.description or "",
        args_schema=tool.args_schema,
    )


def _build_client(*, auth_token: str | None = None) -> Any:
    from langchain_mcp_adapters.client import MultiServerMCPClient
    from langchain_mcp_adapters.sessions import Connection

    connections = cast(dict[str, Connection], build_mcp_connections(auth_token=auth_token))
    return MultiServerMCPClient(
        connections,
        tool_interceptors=[
            AuthHeaderInterceptor(),
            McpToolCallLoggingInterceptor(),
        ],
    )


async def load_platform_mcp_tools(
    *,
    auth_token: str | None = None,
    authorize: bool = True,
) -> list[BaseTool]:
    """连接全部已配置 MCP，返回包装后的 LangChain Tools。"""
    client = _build_client(auth_token=auth_token)
    tools = await client.get_tools()
    logger.info(
        "loaded %s tools from MCP (platform=%s, authorize=%s, servers=%s)",
        len(tools),
        settings.platform_mcp_url,
        authorize,
        list(build_mcp_connections().keys()),
    )
    return [_wrap_mcp_tool(t, authorize=authorize) for t in tools]


async def call_platform_mcp_tool(
    tool_name: str,
    arguments: dict[str, Any],
    *,
    auth_token: str | None = None,
) -> str:
    """经 MCP 调用单个工具（优先用图绑定缓存）。"""
    tools_list = _mcp_tools_cache
    if tools_list is None or not _cache_fresh(_mcp_tools_cache_at):
        tools_list = await load_platform_mcp_tools(auth_token=auth_token, authorize=True)
        _store_graph_cache(tools_list)
    tools = {t.name: t for t in tools_list}
    tool = tools.get(tool_name)
    if tool is None:
        tools_list = await load_platform_mcp_tools(auth_token=auth_token, authorize=True)
        _store_graph_cache(tools_list)
        tools = {t.name: t for t in tools_list}
        tool = tools.get(tool_name)
    if tool is None:
        raise KeyError(f"MCP 无此工具: {tool_name}")
    if auth_token:
        from contracts.context import current_auth_token

        current_auth_token.set(
            auth_token if auth_token.lower().startswith("bearer ") else f"Bearer {auth_token}"
        )
    raw = await tool.ainvoke(arguments) if hasattr(tool, "ainvoke") else tool.invoke(arguments)
    return _extract_tool_text(raw)


def _store_graph_cache(tools: list[BaseTool]) -> None:
    global _mcp_tools_cache, _mcp_tools_cache_at
    _mcp_tools_cache = tools
    _mcp_tools_cache_at = time.monotonic()


def _store_pipeline_cache(tools: list[BaseTool]) -> None:
    global _mcp_pipeline_tools_cache, _mcp_pipeline_tools_cache_at
    _mcp_pipeline_tools_cache = tools
    _mcp_pipeline_tools_cache_at = time.monotonic()


def _load_sync(authorize: bool) -> list[BaseTool]:
    import asyncio

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    loader = lambda: asyncio.run(  # noqa: E731
        load_platform_mcp_tools(authorize=authorize)
    )
    if loop and loop.is_running():
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(loader).result(timeout=60)
    return loader()


def get_mcp_tools_sync(*, force_reload: bool = False) -> list[BaseTool]:
    """图绑定用（含 authorize）。"""
    global _mcp_tools_cache
    if _mcp_tools_cache is not None and not force_reload and _cache_fresh(_mcp_tools_cache_at):
        return list(_mcp_tools_cache)
    tools = _load_sync(authorize=True)
    _store_graph_cache(tools)
    return list(tools)


def get_mcp_pipeline_tools_sync(*, force_reload: bool = False) -> list[BaseTool]:
    """Plan/Pipeline 用（不再二次 authorize）。"""
    global _mcp_pipeline_tools_cache
    if (
        _mcp_pipeline_tools_cache is not None
        and not force_reload
        and _cache_fresh(_mcp_pipeline_tools_cache_at)
    ):
        return list(_mcp_pipeline_tools_cache)
    tools = _load_sync(authorize=False)
    _store_pipeline_cache(tools)
    return list(tools)


def clear_mcp_tools_cache() -> None:
    global _mcp_tools_cache, _mcp_tools_cache_at
    global _mcp_pipeline_tools_cache, _mcp_pipeline_tools_cache_at
    _mcp_tools_cache = None
    _mcp_tools_cache_at = 0.0
    _mcp_pipeline_tools_cache = None
    _mcp_pipeline_tools_cache_at = 0.0


def get_mcp_warmup_status() -> dict[str, Any]:
    return dict(_warmup_status)


async def warmup_mcp_tools() -> dict[str, Any]:
    """启动预热：拉取工具列表并写入缓存。"""
    global _warmup_status
    try:
        tools = await load_platform_mcp_tools(authorize=True)
        _store_graph_cache(tools)
        pipe = await load_platform_mcp_tools(authorize=False)
        _store_pipeline_cache(pipe)
        _warmup_status = {
            "done": True,
            "ok": True,
            "tool_count": len(tools),
            "servers": list(build_mcp_connections().keys()),
            "tool_names": [t.name for t in tools],
            "error": None,
            "cache_ttl_seconds": _cache_ttl_seconds(),
        }
        logger.info("MCP warmup ok: %s tools", len(tools))
    except Exception as exc:  # noqa: BLE001
        _warmup_status = {
            "done": True,
            "ok": False,
            "tool_count": 0,
            "servers": list(build_mcp_connections().keys()),
            "tool_names": [],
            "error": str(exc),
        }
        logger.error("MCP warmup failed: %s", exc)
        # 默认软依赖：仅记录状态，进程继续；AGENT_MCP_REQUIRED=true 才启动失败
        if settings.agent_mcp_required:
            raise
        logger.warning("AGENT_MCP_REQUIRED=false，跳过启动失败；工具调用将在 MCP 就绪后可用")
    return dict(_warmup_status)


async def probe_platform_mcp() -> dict[str, Any]:
    import httpx

    url = (settings.platform_mcp_url or "").rstrip("/")
    if url.endswith("/mcp"):
        health_url = url[: -len("/mcp")] + "/health"
    else:
        health_url = url + "/health"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(health_url)
            ok = resp.status_code == 200
            try:
                body: Any = resp.json()
            except Exception:  # noqa: BLE001
                body = resp.text[:200]
            return {
                "ok": ok,
                "url": settings.platform_mcp_url,
                "health_url": health_url,
                "status_code": resp.status_code,
                "body": body,
                "warmup": get_mcp_warmup_status(),
                "extra_servers": [k for k in build_mcp_connections() if k != "platform"],
            }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "url": settings.platform_mcp_url,
            "health_url": health_url,
            "error": str(exc),
            "warmup": get_mcp_warmup_status(),
        }
