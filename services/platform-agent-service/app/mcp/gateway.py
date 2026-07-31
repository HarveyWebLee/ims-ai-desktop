"""
Agent MCP Gateway（B 面）

1. FastMCP Streamable HTTP：挂载在 `/mcp`（Cursor / MCP Client）
2. JSON REST 兼容：`/api/agent/gateway/*`（脚本友好）

写操作走 agent_chat + HITL；call_platform_tool 仅限只读白名单。
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastmcp import FastMCP
from starlette.requests import Request as StarletteRequest

logger = logging.getLogger(__name__)

_READONLY_PLATFORM_TOOLS = frozenset(
    {
        "query_alarms",
        "get_alarm_detail",
        "query_devices",
        "get_device_detail",
        "query_device_variables",
        "query_device_variable_realtime",
        "query_device_variable_history",
        "retrieve_knowledge",
    }
)

gateway_mcp = FastMCP(
    name="ims-agent-gateway",
    instructions=(
        "综合信息平台 Agent Gateway。"
        "优先用 agent_chat 完成业务；call_platform_tool 仅限只读白名单。"
    ),
)


def _gateway_request_auth() -> tuple[str | None, str | None]:
    """从 FastMCP HTTP 头读取 Authorization 与 X-Agent-Mcp-Key。"""
    try:
        from fastmcp.server.dependencies import get_http_headers

        headers = get_http_headers(include_all=True)
        lower = {str(k).lower(): str(v) for k, v in headers.items()}
        return lower.get("authorization"), lower.get("x-agent-mcp-key")
    except Exception:  # noqa: BLE001
        return None, None


def _is_gateway_authorized(auth: str | None, mcp_key_header: str | None) -> bool:
    """
    Gateway fail-closed：必须持有有效 Bearer JWT，或匹配的 X-Agent-Mcp-Key。

    ``AGENT_MCP_GATEWAY_KEY`` 为空时不再放行匿名调用，仅接受非空 Bearer。
    """
    from app.config import settings

    key = (settings.agent_mcp_gateway_key or "").strip()
    if key and mcp_key_header and mcp_key_header == key:
        return True
    if auth and auth.lower().startswith("bearer ") and auth[7:].strip():
        return True
    return False


def _check_gateway_key_or_bearer(auth: str | None, mcp_key_header: str | None) -> None:
    if _is_gateway_authorized(auth, mcp_key_header):
        return
    raise PermissionError("unauthorized: 需要 Authorization Bearer 或 X-Agent-Mcp-Key")


def _gateway_auth_status() -> dict[str, bool]:
    """供 health 暴露：鉴权是否强制、是否已配置共享密钥。"""
    from app.config import settings

    return {
        "auth_required": True,
        "gateway_key_configured": bool((settings.agent_mcp_gateway_key or "").strip()),
    }


def _audit_gateway(
    *,
    event_type: str,
    tool_name: str | None = None,
    thread_id: str | None = None,
    auth: str | None = None,
    summary: dict[str, Any] | None = None,
) -> None:
    """Gateway 调用写入与 SSE 同一 audit_store。"""
    try:
        from app.middleware.auth import resolve_user_id_from_token
        from app.services.audit_store import audit_store, mask_payload_summary

        tid = (thread_id or "mcp-gateway").strip() or "mcp-gateway"
        audit_store.append(
            thread_id=tid,
            user_id=resolve_user_id_from_token(auth),
            event_type=event_type,
            tool_name=tool_name,
            payload_summary=mask_payload_summary(summary or {}),
        )
    except Exception:  # noqa: BLE001
        logger.debug("gateway audit skip", exc_info=True)


async def _list_platform_tools_impl(auth: str | None) -> str:
    from app.mcp.client import load_platform_mcp_tools
    from app.mcp.local_tools import build_retrieve_knowledge_tool

    tools = await load_platform_mcp_tools(auth_token=auth)
    local = build_retrieve_knowledge_tool()
    if all(t.name != local.name for t in tools):
        tools = list(tools) + [local]
    return json.dumps(
        {"tools": [{"name": t.name, "description": (t.description or "")[:500]} for t in tools]},
        ensure_ascii=False,
    )


async def _call_readonly_platform_tool(
    tool_name: str,
    arguments: dict[str, Any] | None,
    auth: str | None,
) -> str:
    name = (tool_name or "").strip()
    args = arguments if isinstance(arguments, dict) else {}
    if name not in _READONLY_PLATFORM_TOOLS:
        raise PermissionError(f"工具不在只读白名单: {name}")

    if name == "retrieve_knowledge":
        from app.mcp.local_tools import build_retrieve_knowledge_tool
        from contracts.context import current_auth_token

        if auth:
            current_auth_token.set(auth)
        raw = build_retrieve_knowledge_tool().invoke(args)
        return raw if isinstance(raw, str) else str(raw)

    from app.mcp.client import call_platform_mcp_tool

    return await call_platform_mcp_tool(name, args, auth_token=auth)


async def _agent_chat_impl(
    message: str,
    thread_id: str,
    model: str,
    auth: str | None,
) -> str:
    from app.application.conversation.chat import stream_chat
    from app.models.catalog import get_default_model_id

    text = (message or "").strip()
    if not text:
        raise ValueError("message 必填")
    model_id = (model or "").strip() or get_default_model_id()
    tid = thread_id or "mcp-gateway"
    chunks: list[str] = []
    async for event_name, data in stream_chat(
        thread_id=tid,
        model_id=model_id,
        message=text,
        metadata={},
        auth_token=auth,
    ):
        if event_name == "message" and isinstance(data, dict) and data.get("content"):
            chunks.append(str(data["content"]))
    return json.dumps(
        {"thread_id": tid, "content": "".join(chunks)},
        ensure_ascii=False,
    )


async def _agent_resume_impl(
    thread_id: str,
    payload: dict[str, Any] | None,
    model: str,
    auth: str | None,
) -> str:
    from app.application.conversation.resume import stream_resume
    from app.models.catalog import get_default_model_id

    tid = (thread_id or "").strip()
    if not tid:
        raise ValueError("thread_id 必填")
    model_id = (model or "").strip() or get_default_model_id()
    chunks: list[str] = []
    async for event_name, data in stream_resume(
        thread_id=tid,
        model_id=model_id,
        resume_value=payload if isinstance(payload, dict) else {},
        auth_token=auth,
    ):
        if event_name == "message" and isinstance(data, dict) and data.get("content"):
            chunks.append(str(data["content"]))
    return json.dumps({"thread_id": tid, "content": "".join(chunks)}, ensure_ascii=False)


async def _dispatch_named_tool(name: str, arguments: dict[str, Any], auth: str | None) -> str:
    if name == "list_platform_tools":
        return await _list_platform_tools_impl(auth)
    if name == "call_platform_tool":
        return await _call_readonly_platform_tool(
            str(arguments.get("tool_name") or ""),
            arguments.get("arguments") if isinstance(arguments.get("arguments"), dict) else {},
            auth,
        )
    if name == "agent_chat":
        return await _agent_chat_impl(
            str(arguments.get("message") or ""),
            str(arguments.get("thread_id") or "mcp-gateway"),
            str(arguments.get("model") or ""),
            auth,
        )
    if name == "agent_resume":
        return await _agent_resume_impl(
            str(arguments.get("thread_id") or ""),
            arguments.get("payload") if isinstance(arguments.get("payload"), dict) else {},
            str(arguments.get("model") or ""),
            auth,
        )
    raise KeyError(f"未知 Gateway 工具: {name}")


@gateway_mcp.tool(
    name="list_platform_tools",
    description="列出 Platform MCP（及额外 MCP）工具名与描述",
)
async def gw_list_platform_tools() -> str:
    auth, mcp_key = _gateway_request_auth()
    _check_gateway_key_or_bearer(auth, mcp_key)
    text = await _list_platform_tools_impl(auth)
    _audit_gateway(event_type="mcp_gateway_list_tools", auth=auth, summary={"ok": True})
    return text


@gateway_mcp.tool(
    name="call_platform_tool",
    description="经 MCP 调用只读工具；参数 tool_name、arguments(JSON 对象)",
)
async def gw_call_platform_tool(tool_name: str, arguments: dict[str, Any] | None = None) -> str:
    auth, mcp_key = _gateway_request_auth()
    _check_gateway_key_or_bearer(auth, mcp_key)
    text = await _call_readonly_platform_tool(tool_name, arguments, auth)
    _audit_gateway(
        event_type="mcp_gateway_call_tool",
        tool_name=tool_name,
        auth=auth,
        summary={"ok": True, "tool": tool_name},
    )
    return text


@gateway_mcp.tool(
    name="agent_chat",
    description="发起一轮 Agent 对话并聚合文本；参数 message、thread_id?、model?",
)
async def gw_agent_chat(
    message: str,
    thread_id: str = "mcp-gateway",
    model: str = "",
) -> str:
    auth, mcp_key = _gateway_request_auth()
    _check_gateway_key_or_bearer(auth, mcp_key)
    text = await _agent_chat_impl(message, thread_id, model, auth)
    _audit_gateway(
        event_type="mcp_gateway_chat",
        thread_id=thread_id,
        auth=auth,
        summary={"ok": True},
    )
    return text


@gateway_mcp.tool(
    name="agent_resume",
    description="HITL 续跑；参数 thread_id、payload、model?",
)
async def gw_agent_resume(
    thread_id: str,
    payload: dict[str, Any] | None = None,
    model: str = "",
) -> str:
    auth, mcp_key = _gateway_request_auth()
    _check_gateway_key_or_bearer(auth, mcp_key)
    text = await _agent_resume_impl(thread_id, payload, model, auth)
    _audit_gateway(
        event_type="mcp_gateway_resume",
        thread_id=thread_id,
        auth=auth,
        summary={"ok": True},
    )
    return text


@gateway_mcp.resource("gateway://capabilities")
def gateway_capabilities() -> str:
    """Gateway 能力说明（MCP Resource）。"""
    return json.dumps(
        {
            "tools": [
                "agent_chat",
                "agent_resume",
                "list_platform_tools",
                "call_platform_tool",
            ],
            "readonly_whitelist": sorted(_READONLY_PLATFORM_TOOLS),
            "note": "写操作请走 agent_chat，由 Agent 图 + HITL 约束",
        },
        ensure_ascii=False,
        indent=2,
    )


@gateway_mcp.custom_route("/health", methods=["GET"])
async def mcp_app_health(_request: StarletteRequest) -> JSONResponse:
    from app.mcp.client import probe_platform_mcp

    platform = await probe_platform_mcp()
    return JSONResponse(
        {
            "ok": True,
            "gateway": "agent-mcp",
            "transport": "streamable-http",
            "platform_mcp": platform,
            **_gateway_auth_status(),
        }
    )


def create_gateway_http_app():
    """Streamable HTTP ASGI 应用，供 FastAPI mount。"""
    return gateway_mcp.http_app(path="/", transport="streamable-http")


def _set_auth_context(request: Request) -> None:
    auth = request.headers.get("authorization")
    if auth:
        from contracts.context import current_auth_token

        current_auth_token.set(auth)


def _rest_auth_error(request: Request) -> str | None:
    auth = request.headers.get("authorization") or ""
    mcp_key = request.headers.get("x-agent-mcp-key") or ""
    if _is_gateway_authorized(auth, mcp_key):
        return None
    return "unauthorized"


def mount_agent_mcp_gateway(app: FastAPI) -> None:
    """挂载 JSON REST 兼容层（真 MCP Streamable HTTP 见 mount_gateway_streamable_http）。"""

    @app.get("/api/agent/gateway/health")
    async def gateway_health() -> dict[str, Any]:
        from app.mcp.client import probe_platform_mcp

        platform = await probe_platform_mcp()
        return {
            "ok": True,
            "gateway": "agent-mcp",
            "mcp_streamable_http": "/mcp",
            "platform_mcp": platform,
            **_gateway_auth_status(),
            "tools": [
                "agent_chat",
                "agent_resume",
                "list_platform_tools",
                "call_platform_tool",
            ],
        }

    @app.post("/api/agent/gateway/tools/list")
    async def list_tools_rest(request: Request) -> JSONResponse:
        err = _rest_auth_error(request)
        if err:
            return JSONResponse({"code": 401, "data": None, "message": err}, status_code=401)
        _set_auth_context(request)
        text = await _list_platform_tools_impl(request.headers.get("authorization"))
        return JSONResponse({"code": 0, "data": json.loads(text), "message": ""})

    @app.post("/api/agent/gateway/tools/call")
    async def call_tool_rest(request: Request) -> JSONResponse:
        err = _rest_auth_error(request)
        if err:
            return JSONResponse({"code": 401, "data": None, "message": err}, status_code=401)
        _set_auth_context(request)
        body = await request.json()
        name = str(body.get("name") or "")
        arguments = body.get("arguments") or {}
        if not isinstance(arguments, dict):
            arguments = {}
        auth = request.headers.get("authorization")
        try:
            text = await _dispatch_named_tool(name, arguments, auth)
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                data = {"result": text}
            return JSONResponse({"code": 0, "data": data, "message": ""})
        except Exception as exc:  # noqa: BLE001
            logger.exception("gateway REST tool %s failed", name)
            return JSONResponse(
                {"code": 1, "data": None, "message": str(exc)},
                status_code=500,
            )


def mount_gateway_streamable_http(app: FastAPI) -> Any:
    """
    将 FastMCP ASGI 挂到 `/mcp`。

    注意：须在创建 FastAPI 时合并 lifespan（见 main.py）。
    返回 http_app 以便合并 lifespan。
    """
    mcp_http = create_gateway_http_app()
    app.mount("/mcp", mcp_http)
    return mcp_http
