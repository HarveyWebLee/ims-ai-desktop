"""MCP Client / Gateway 单元测试（不依赖真实 Platform MCP 进程）。"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_auth_header_interceptor_injects_bearer_and_thread():
    from langchain_mcp_adapters.interceptors import MCPToolCallRequest

    from app.mcp.client import AuthHeaderInterceptor
    from contracts.context import current_auth_token, current_thread_id

    captured: dict[str, Any] = {}

    async def handler(request):
        captured["headers"] = dict(request.headers or {})
        return MagicMock()

    token = current_auth_token.set("raw-jwt-token")
    tid = current_thread_id.set("thread-abc")
    from contracts.context import current_recent_user_messages, current_user_utterance

    utt = current_user_utterance.set("帮我导出")
    recent = current_recent_user_messages.set(("查告警",))
    try:
        from contracts.context import decode_http_header_value, encode_http_header_value

        interceptor = AuthHeaderInterceptor()
        req = MCPToolCallRequest(name="noop", args={}, server_name="platform", headers={})
        await interceptor(req, handler)
        assert captured["headers"].get("Authorization") == "Bearer raw-jwt-token"
        assert captured["headers"].get("X-Thread-Id") == "thread-abc"
        # 中文须百分号编码，保证 httpx 头值为 ASCII
        encoded_utt = captured["headers"].get("X-User-Utterance") or ""
        assert encoded_utt == encode_http_header_value("帮我导出")
        assert encoded_utt.isascii()
        assert decode_http_header_value(encoded_utt) == "帮我导出"
        encoded_recent = captured["headers"].get("X-Recent-User-Messages") or ""
        assert encoded_recent.isascii()
        assert "查告警" in decode_http_header_value(encoded_recent)
    finally:
        current_auth_token.reset(token)
        current_thread_id.reset(tid)
        current_user_utterance.reset(utt)
        current_recent_user_messages.reset(recent)


@pytest.mark.asyncio
async def test_gateway_readonly_rejects_write_tool():
    from app.mcp.gateway import _call_readonly_platform_tool

    with pytest.raises(PermissionError):
        await _call_readonly_platform_tool("send_device_cmd", {}, None)


def test_build_mcp_connections_includes_platform_and_extra(monkeypatch):
    from app.config import settings
    from app.mcp.connections import build_mcp_connections

    monkeypatch.setattr(settings, "platform_mcp_url", "http://127.0.0.1:8010/mcp")
    monkeypatch.setattr(
        settings,
        "agent_mcp_extra_servers_json",
        '{"ext":{"transport":"streamable_http","url":"http://127.0.0.1:8020/mcp"}}',
    )
    conns = build_mcp_connections(auth_token="Bearer t")
    assert "platform" in conns
    assert conns["platform"]["url"] == "http://127.0.0.1:8010/mcp"
    assert conns["platform"]["headers"]["Authorization"] == "Bearer t"
    assert "ext" in conns
    assert conns["ext"]["url"] == "http://127.0.0.1:8020/mcp"


def test_build_mcp_connections_rejects_overwrite_platform(monkeypatch):
    from app.config import settings
    from app.mcp.connections import build_mcp_connections

    monkeypatch.setattr(
        settings,
        "agent_mcp_extra_servers_json",
        '{"platform":{"transport":"streamable_http","url":"http://evil"}}',
    )
    conns = build_mcp_connections()
    assert conns["platform"]["url"] != "http://evil"


def test_gateway_rest_auth_requires_key_when_configured(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.config import settings
    from app.mcp.gateway import mount_agent_mcp_gateway

    monkeypatch.setattr(settings, "agent_mcp_gateway_key", "secret-key")
    app = FastAPI()
    mount_agent_mcp_gateway(app)
    client = TestClient(app)

    denied = client.post("/api/agent/gateway/tools/list")
    assert denied.status_code == 401

    with patch(
        "app.mcp.gateway._list_platform_tools_impl",
        return_value='{"tools":[]}',
    ):
        ok = client.post(
            "/api/agent/gateway/tools/list",
            headers={"X-Agent-Mcp-Key": "secret-key"},
        )
    assert ok.status_code == 200
    assert ok.json()["code"] == 0


def test_gateway_rest_auth_fail_closed_when_key_empty(monkeypatch):
    """密钥为空时仍须 Bearer，匿名调用 401。"""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.config import settings
    from app.mcp.gateway import mount_agent_mcp_gateway

    monkeypatch.setattr(settings, "agent_mcp_gateway_key", "")
    app = FastAPI()
    mount_agent_mcp_gateway(app)
    client = TestClient(app)

    denied = client.post("/api/agent/gateway/tools/list")
    assert denied.status_code == 401

    health = client.get("/api/agent/gateway/health")
    assert health.status_code == 200
    body = health.json()
    assert body["auth_required"] is True
    assert body["gateway_key_configured"] is False

    with patch(
        "app.mcp.gateway._list_platform_tools_impl",
        return_value='{"tools":[]}',
    ):
        ok = client.post(
            "/api/agent/gateway/tools/list",
            headers={"Authorization": "Bearer test-jwt"},
        )
    assert ok.status_code == 200
    assert ok.json()["code"] == 0


def test_check_gateway_rejects_anonymous_even_without_key(monkeypatch):
    from app.config import settings
    from app.mcp.gateway import _check_gateway_key_or_bearer

    monkeypatch.setattr(settings, "agent_mcp_gateway_key", "")
    with pytest.raises(PermissionError, match="unauthorized"):
        _check_gateway_key_or_bearer(None, None)
    _check_gateway_key_or_bearer("Bearer abc", None)


def test_maybe_raise_hitl_from_mcp_json(monkeypatch):
    from app.graph import hitl_interrupt
    from app.mcp.client import _maybe_raise_hitl

    seen: list[dict] = []

    def fake_interrupt(payload):
        seen.append(payload)
        return {"type": "approve"}

    monkeypatch.setattr(hitl_interrupt, "interrupt_or_raise", fake_interrupt)
    out = _maybe_raise_hitl(
        '{"ok":false,"hitl_required":true,"payload":{"type":"ask_params","tool":"x"}}'
    )
    assert seen and seen[0]["type"] == "ask_params"
    assert "hitl_required" in out or out  # interrupt 后仍返回原文（无 invoke_again）


def test_extract_hitl_payload_from_mcp_json():
    from app.mcp.client import _extract_hitl_payload

    assert _extract_hitl_payload('{"ok":true}') is None
    payload = _extract_hitl_payload(
        '{"ok":false,"hitl_required":true,"payload":{"type":"confirm","tool":"send_device_cmd"}}'
    )
    assert payload == {"type": "confirm", "tool": "send_device_cmd"}


def test_resolve_mcp_hitl_reinvokes_after_approve(monkeypatch):
    """图内 resume 批准后应带 bypass 重调 MCP，而不是把 hitl 信封当结果。"""
    from app.mcp import client as mcp_client
    from contracts.context import current_hitl_confirm_bypass

    calls: list[dict] = []

    def fake_interrupt(payload):
        assert payload["type"] == "confirm"
        return {"type": "approve", "approved": True}

    monkeypatch.setattr(
        "app.graph.hitl_interrupt.interrupt_or_raise",
        fake_interrupt,
    )

    def invoke_again(args: dict) -> str:
        calls.append(dict(args))
        assert current_hitl_confirm_bypass.get() is True
        return '{"ok":true,"summary":"已下发"}'

    out = mcp_client._resolve_mcp_hitl_text(
        '{"ok":false,"hitl_required":true,"payload":{"type":"confirm","tool":"send_device_cmd"}}',
        tool_name="send_device_cmd",
        kwargs={"device_code": "zhonglian_108", "action": "open_door"},
        invoke_again=invoke_again,
    )
    assert '"ok": true' in out.replace(" ", "") or '"ok":true' in out
    assert len(calls) == 1
    assert calls[0]["device_code"] == "zhonglian_108"
    assert "type" not in calls[0]
    assert "approved" not in calls[0]


def test_gateway_request_auth_reads_mcp_key(monkeypatch):
    from app.mcp import gateway as gw

    monkeypatch.setattr(
        "fastmcp.server.dependencies.get_http_headers",
        lambda include_all=True: {
            "Authorization": "Bearer jwt",
            "X-Agent-Mcp-Key": "k1",
        },
    )
    auth, key = gw._gateway_request_auth()
    assert auth == "Bearer jwt"
    assert key == "k1"


def test_get_tool_by_name_prefers_mcp(monkeypatch):
    from app.services import agent_tool_retry as atr

    class _T:
        name = "query_alarms"

        def invoke(self, args):
            return '{"ok":true}'

    monkeypatch.setattr(
        "app.mcp.client.get_mcp_pipeline_tools_sync",
        lambda force_reload=False: [_T()],
    )
    tool = atr.get_tool_by_name("query_alarms")
    assert tool is not None
    assert tool.name == "query_alarms"
    assert atr.invoke_tool_sync("query_alarms", {}) == '{"ok":true}'


def test_get_tool_by_name_no_raw_fallback_when_mcp_down(monkeypatch):
    from app.services import agent_tool_retry as atr

    def _boom(**_kwargs):
        raise RuntimeError("mcp down")

    monkeypatch.setattr("app.mcp.client.get_mcp_pipeline_tools_sync", _boom)
    assert atr.get_tool_by_name("navigate_to") is None


@pytest.mark.asyncio
async def test_wrap_mcp_tool_sync_bridges_async_only_structured_tool():
    """底层 MCP 工具仅有 coroutine 时，包装后的 sync invoke 不得抛 sync invocation 错误。"""
    from langchain_core.tools import StructuredTool

    from app.mcp.client import _wrap_mcp_tool

    async def _only_async(**kwargs):
        return json.dumps({"ok": True, "summary": "async-ok", "args": kwargs})

    inner = StructuredTool.from_function(
        coroutine=_only_async,
        name="query_alarms",
        description="test",
    )
    # 确认底层确实不支持 sync
    with pytest.raises(NotImplementedError, match="does not support sync invocation"):
        inner.invoke({"start_time": "近一小时"})

    wrapped = _wrap_mcp_tool(inner, authorize=False)
    result = wrapped.invoke({"start_time": "近一小时"})
    data = json.loads(result)
    assert data["ok"] is True
    assert data["summary"] == "async-ok"

    aresult = await wrapped.ainvoke({"start_time": "近一小时"})
    assert json.loads(aresult)["ok"] is True


@pytest.mark.asyncio
async def test_auth_interceptor_injects_hitl_bypass():
    from langchain_mcp_adapters.interceptors import MCPToolCallRequest

    from app.mcp.client import AuthHeaderInterceptor
    from contracts.context import current_hitl_confirm_bypass

    captured: dict = {}

    async def handler(request):
        captured["headers"] = dict(request.headers or {})
        return MagicMock()

    token = current_hitl_confirm_bypass.set(True)
    try:
        req = MCPToolCallRequest(name="noop", args={}, server_name="platform", headers={})
        await AuthHeaderInterceptor()(req, handler)
        assert captured["headers"].get("X-Hitl-Confirm-Bypass") == "1"
    finally:
        current_hitl_confirm_bypass.reset(token)
