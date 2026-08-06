"""工具 schema 两段式中间件单测。"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from langchain_core.tools import StructuredTool
from langgraph.types import Command
from pydantic import BaseModel, Field


class _QueryArgs(BaseModel):
    device_code: str = Field(description="设备编码")
    limit: int = Field(default=10, description="条数")


def _make_full_tool() -> StructuredTool:
    def _run(device_code: str, limit: int = 10) -> str:
        return f"ok:{device_code}:{limit}"

    return StructuredTool.from_function(
        func=_run,
        name="query_device",
        description="查询设备详情与状态。用于运维排查时按编码拉取设备信息。",
        args_schema=_QueryArgs,
    )


def test_shorten_tool_description_takes_first_sentence() -> None:
    from app.services.tool_schema_phase import shorten_tool_description

    text = "查询设备详情与状态。用于运维排查时按编码拉取设备信息。"
    assert shorten_tool_description(text) == "查询设备详情与状态。"


def test_stub_has_empty_schema_and_short_description() -> None:
    from app.services.tool_schema_phase import build_schema_stub_tool, tool_args_json_schema

    full = _make_full_tool()
    stub = build_schema_stub_tool(full)
    assert stub.name == "query_device"
    assert "运维排查" not in (stub.description or "")
    stub_schema = tool_args_json_schema(stub)
    props = stub_schema.get("properties") or {}
    assert props == {} or list(props.keys()) == []
    full_schema = tool_args_json_schema(full)
    assert "device_code" in (full_schema.get("properties") or {})


def test_wrap_model_call_exposes_stub_until_unlocked() -> None:
    from app.services.tool_schema_phase import ToolSchemaPhaseMiddleware

    full = _make_full_tool()
    mw = ToolSchemaPhaseMiddleware([full])
    captured: dict[str, Any] = {}

    def handler(request: Any) -> Any:
        captured["tools"] = list(request.tools)
        return "ok"

    req = MagicMock()
    req.tools = [full]
    req.state = {"unlocked_tool_names": []}
    req.override = lambda **kwargs: MagicMock(tools=kwargs["tools"], state=req.state)

    mw.wrap_model_call(req, handler)  # type: ignore[arg-type]
    assert len(captured["tools"]) == 1
    assert captured["tools"][0].name == "query_device"
    from app.services.tool_schema_phase import tool_args_json_schema

    assert "device_code" not in (
        tool_args_json_schema(captured["tools"][0]).get("properties") or {}
    )

    req2 = MagicMock()
    req2.tools = [full]
    req2.state = {"unlocked_tool_names": ["query_device"]}
    req2.override = lambda **kwargs: MagicMock(tools=kwargs["tools"], state=req2.state)
    captured.clear()
    mw.wrap_model_call(req2, handler)  # type: ignore[arg-type]
    assert "device_code" in (tool_args_json_schema(captured["tools"][0]).get("properties") or {})


def test_first_call_unlocks_without_running_tool() -> None:
    from app.services.tool_schema_phase import ToolSchemaPhaseMiddleware

    full = _make_full_tool()
    mw = ToolSchemaPhaseMiddleware([full])
    ran = {"n": 0}

    def handler(_request: Any) -> str:
        ran["n"] += 1
        return "should-not-run"

    req = MagicMock()
    req.tool_call = {"name": "query_device", "id": "call-1", "args": {}}
    req.state = {"unlocked_tool_names": []}
    result = mw.wrap_tool_call(req, handler)  # type: ignore[arg-type]
    assert ran["n"] == 0
    assert isinstance(result, Command)
    update = result.update or {}
    assert "query_device" in (update.get("unlocked_tool_names") or [])
    messages = update.get("messages") or []
    assert len(messages) == 1
    assert "device_code" in str(messages[0].content)
    assert "JSON Schema" in str(messages[0].content)


def test_unlocked_call_runs_full_tool() -> None:
    from app.services.tool_schema_phase import ToolSchemaPhaseMiddleware

    full = _make_full_tool()
    mw = ToolSchemaPhaseMiddleware([full])
    ran = {"tool": None}

    def handler(request: Any) -> str:
        ran["tool"] = request.tool
        return "ran"

    req = MagicMock()
    req.tool_call = {
        "name": "query_device",
        "id": "call-2",
        "args": {"device_code": "D1", "limit": 1},
    }
    req.state = {"unlocked_tool_names": ["query_device"]}
    req.override = lambda **kwargs: MagicMock(
        tool=kwargs.get("tool"),
        tool_call=req.tool_call,
        state=req.state,
    )
    out = mw.wrap_tool_call(req, handler)  # type: ignore[arg-type]
    assert out == "ran"
    assert ran["tool"] is full


def test_before_agent_clears_when_reset_flag() -> None:
    from app.services.tool_schema_phase import (
        ToolSchemaPhaseMiddleware,
        current_schema_phase_reset,
    )

    full = _make_full_tool()
    mw = ToolSchemaPhaseMiddleware([full])
    token = current_schema_phase_reset.set(True)
    try:
        update = mw.before_agent({"unlocked_tool_names": ["query_device"]}, None)  # type: ignore[arg-type]
        assert update == {"unlocked_tool_names": []}
    finally:
        current_schema_phase_reset.reset(token)

    token2 = current_schema_phase_reset.set(False)
    try:
        assert mw.before_agent({"unlocked_tool_names": ["query_device"]}, None) is None  # type: ignore[arg-type]
    finally:
        current_schema_phase_reset.reset(token2)


def test_retrieve_knowledge_always_full() -> None:
    from app.services.tool_schema_phase import (
        ALWAYS_FULL_SCHEMA_TOOLS,
        ToolSchemaPhaseMiddleware,
        tool_args_json_schema,
    )

    def _run(query: str, top_k: int = 4) -> str:
        return query

    rag = StructuredTool.from_function(
        func=_run,
        name="retrieve_knowledge",
        description="知识检索",
    )
    assert "retrieve_knowledge" in ALWAYS_FULL_SCHEMA_TOOLS
    mw = ToolSchemaPhaseMiddleware([rag])
    captured: dict[str, Any] = {}

    def handler(request: Any) -> Any:
        captured["tools"] = list(request.tools)
        return "ok"

    req = MagicMock()
    req.tools = [rag]
    req.state = {"unlocked_tool_names": []}
    req.override = lambda **kwargs: MagicMock(tools=kwargs["tools"], state=req.state)
    mw.wrap_model_call(req, handler)  # type: ignore[arg-type]
    props = tool_args_json_schema(captured["tools"][0]).get("properties") or {}
    assert "query" in props


def test_build_middleware_respects_feature_flag(monkeypatch: Any) -> None:
    from app.config import settings
    from app.services.tool_schema_phase import build_tool_schema_phase_middleware

    full = _make_full_tool()
    monkeypatch.setattr(settings, "agent_tool_schema_twophase", False)
    assert build_tool_schema_phase_middleware([full]) is None
    monkeypatch.setattr(settings, "agent_tool_schema_twophase", True)
    assert build_tool_schema_phase_middleware([full]) is not None
