"""将 platform_mcp.runtime.tools 注册为 FastMCP Tools（本进程执行、对外 MCP）。"""

from __future__ import annotations

import functools
import inspect
import json
import logging
import os
from pathlib import Path
from typing import Any

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from platform_mcp.config import settings

logger = logging.getLogger(__name__)

_WRITE_TOOLS = frozenset(
    {
        "download_file",
        "batch_confirm_alarms",
        "batch_process_alarms",
        "send_device_cmd",
    }
)

mcp = FastMCP(
    name="ims-platform-tools",
    instructions="综合信息平台告警/设备/导出/导航等业务工具。返回统一 ToolResult JSON。",
)


def _sync_runtime_env() -> None:
    """把 MCP Server 配置注入 runtime Settings 可读的环境变量。"""
    if settings.platform_api_base:
        os.environ.setdefault("PLATFORM_API_BASE", settings.platform_api_base)
    if settings.agent_service_root:
        data_dir = Path(settings.agent_service_root) / "app" / "data"
        os.environ.setdefault("AGENT_DATA_DIR", str(data_dir))
        os.environ.setdefault("AGENT_SERVICE_ROOT", settings.agent_service_root)


def _serialize_result(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, default=str)


def _catalog_json_path() -> Path:
    from contracts.paths import mcp_catalog_path

    path = mcp_catalog_path()
    if path.is_file():
        return path
    fallback = Path(settings.agent_service_root) / "app" / "tools" / "catalog.json"
    return fallback if fallback.is_file() else path


def _load_catalog_descriptions() -> dict[str, str]:
    catalog_path = _catalog_json_path()
    if not catalog_path.is_file():
        return {}
    try:
        data = json.loads(catalog_path.read_text(encoding="utf-8"))
    except OSError, json.JSONDecodeError:
        return {}
    out: dict[str, str] = {}
    tools = data if isinstance(data, list) else data.get("tools") or data.get("items") or []
    if isinstance(data, dict) and not tools:
        for key, val in data.items():
            if isinstance(val, dict) and (val.get("description") or val.get("name")):
                name = str(val.get("name") or key)
                desc = str(val.get("description") or "")
                risk = val.get("risk_level")
                if risk:
                    desc = f"[risk={risk}] {desc}".strip()
                out[name] = desc
        return out
    for item in tools:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "")
        if not name:
            continue
        desc = str(item.get("description") or "")
        risk = item.get("risk_level")
        if risk:
            desc = f"[risk={risk}] {desc}".strip()
        out[name] = desc
    return out


def _apply_request_auth_context() -> str | None:
    from fastmcp.server.dependencies import get_http_headers

    headers = get_http_headers(include_all=True)
    lower = {str(k).lower(): str(v) for k, v in headers.items()}
    auth = lower.get("authorization") or None
    thread_id = lower.get("x-thread-id") or None
    bypass_raw = (lower.get("x-hitl-confirm-bypass") or "").strip().lower()
    run_mode_raw = lower.get("x-run-mode") or None

    from contracts.context import (
        current_auth_token,
        current_hitl_confirm_bypass,
        current_run_mode,
        current_thread_id,
        normalize_run_mode,
    )

    if auth:
        current_auth_token.set(auth)
    if thread_id:
        current_thread_id.set(thread_id)
    if bypass_raw in {"1", "true", "yes", "on"}:
        current_hitl_confirm_bypass.set(True)
    current_run_mode.set(normalize_run_mode(run_mode_raw))
    return auth


def _wrap_tool_callable(bound_tool: Any):
    from contracts.hitl import McpHitlSignal

    base_fn = getattr(bound_tool, "func", None) or getattr(bound_tool, "coroutine", None)
    if base_fn is None:
        raise RuntimeError(f"工具无底层函数: {bound_tool.name}")

    sig = inspect.signature(base_fn)
    tool_name = bound_tool.name

    @functools.wraps(base_fn)
    def handler(*args: Any, **kwargs: Any) -> str:
        auth = _apply_request_auth_context()
        if tool_name in _WRITE_TOOLS and not (auth and auth.strip()):
            return json.dumps(
                {
                    "ok": False,
                    "summary": "写操作需要 Authorization: Bearer <jwt>",
                    "data": {"error": "unauthorized"},
                },
                ensure_ascii=False,
            )

        bound = sig.bind_partial(*args, **kwargs)
        bound.apply_defaults()
        payload = dict(bound.arguments)
        payload.pop("self", None)
        payload.pop("cls", None)
        try:
            result = bound_tool.invoke(payload)
            return _serialize_result(result)
        except McpHitlSignal as exc:
            return json.dumps(
                {
                    "ok": False,
                    "summary": str(exc),
                    "hitl_required": True,
                    "payload": exc.payload,
                },
                ensure_ascii=False,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("MCP tool %s failed", tool_name)
            return json.dumps(
                {
                    "ok": False,
                    "summary": f"工具执行失败: {exc}",
                    "data": {"error": type(exc).__name__},
                },
                ensure_ascii=False,
            )

    handler.__signature__ = sig  # type: ignore[attr-defined]
    handler.__name__ = tool_name
    handler.__doc__ = bound_tool.description or tool_name
    return handler


def _validate_catalog_vs_tools(registered: list[str]) -> None:
    """启动时校验 catalog 工具名与已注册工具一致（忽略 retrieve_knowledge）。"""
    path = _catalog_json_path()
    if not path.is_file():
        logger.warning("catalog 缺失，跳过校验: %s", path)
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("catalog 无法解析: %s", exc)
        return
    items = data if isinstance(data, list) else []
    catalog_names = {
        str(item.get("name"))
        for item in items
        if isinstance(item, dict) and item.get("enabled", True) and item.get("name")
    }
    reg = set(registered)
    missing = sorted(catalog_names - reg)
    extra = sorted(reg - catalog_names)
    if missing or extra:
        logger.warning(
            "catalog↔tools 不一致 missing=%s extra=%s",
            missing,
            extra,
        )
    else:
        logger.info("catalog↔tools 校验通过: %s tools", len(reg))


def _register_langchain_tools() -> None:
    _sync_runtime_env()

    from platform_mcp.runtime.tools.registry import get_platform_tools

    catalog_desc = _load_catalog_descriptions()
    registered: list[str] = []

    for tool in get_platform_tools():
        handler = _wrap_tool_callable(tool)
        description = catalog_desc.get(tool.name) or tool.description or tool.name
        mcp.tool(name=tool.name, description=description)(handler)
        registered.append(tool.name)
        logger.info("registered MCP tool: %s", tool.name)

    _validate_catalog_vs_tools(registered)


def _read_tools_catalog() -> Any:
    path = _catalog_json_path()
    if not path.is_file():
        return {"tools": [], "error": f"catalog missing: {path}"}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"tools": [], "error": str(exc)}


@mcp.resource("catalog://tools")
def resource_tools_catalog() -> str:
    return json.dumps(_read_tools_catalog(), ensure_ascii=False, indent=2)


@mcp.resource("catalog://write-tools")
def resource_write_tools() -> str:
    return json.dumps(sorted(_WRITE_TOOLS), ensure_ascii=False, indent=2)


@mcp.prompt(name="platform_ops")
def prompt_platform_ops() -> str:
    return (
        "你正在通过 Platform MCP 操作综合信息平台。\n"
        "- 查询类：query_alarms / query_devices / get_* / query_device_variables / query_device_variable_realtime / query_device_variable_history\n"
        "- 写操作：download_file / batch_* / send_device_cmd，必须带 Authorization\n"
        "- 缺参或高风险确认由上游 Agent HITL 处理，本 Server 只返回 hitl_required JSON\n"
        "- Client 动作（navigate_to 等）返回 client_action，由前端执行\n"
    )


@mcp.custom_route("/health", methods=["GET"])
async def health(_request: Request) -> JSONResponse:
    catalog_path = _catalog_json_path()
    return JSONResponse(
        {
            "status": "ok",
            "service": "platform-mcp-server",
            "mcp": "/mcp",
            "port": settings.port,
            "execution": "platform_mcp.runtime.tools + contracts",
            "catalog": str(catalog_path),
            "catalog_exists": catalog_path.is_file(),
            "resources": ["catalog://tools", "catalog://write-tools"],
            "prompts": ["platform_ops"],
        }
    )


_register_langchain_tools()
