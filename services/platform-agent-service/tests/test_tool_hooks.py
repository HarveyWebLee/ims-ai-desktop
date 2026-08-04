"""P2-1：运行时工具 Hooks（审计 / 拦截）。"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from app.application.tool_execution import ToolExecutionPipeline
from app.config import settings
from app.domain.tool_execution import ToolExecutionContext, ToolExecutionRequest
from app.domain.tool_hooks import ToolHookDecision
from app.services.tool_hooks import (
    AuditToolHook,
    CompositeToolHook,
    DenyListToolHook,
    configure_tool_hooks,
    reset_tool_hooks,
    run_after_tool_hooks,
    run_before_tool_hooks,
)


@pytest.fixture(autouse=True)
def _reset_hooks():
    reset_tool_hooks()
    yield
    reset_tool_hooks()


def test_deny_list_hook_blocks_and_audits(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "agent_tool_hooks_enabled", True)
    monkeypatch.setattr(settings, "agent_tool_hook_deny_tools", "download_file")
    monkeypatch.setattr(settings, "agent_tool_hooks_audit_after", False)
    reset_tool_hooks()

    append = MagicMock()
    with patch("app.services.audit_store.audit_store") as store:
        store.append = append
        denied = run_before_tool_hooks(
            "download_file",
            {"path": "/x"},
            context=ToolExecutionContext(thread_id="t-hooks-1", principal_id="u1"),
        )
    assert denied is not None
    body = json.loads(denied)
    assert body["ok"] is False
    assert body["data"]["error_code"] == "tool_hook_deny_list"
    append.assert_called()
    assert append.call_args.kwargs["event_type"] == "tool_hook_deny"
    assert run_before_tool_hooks("query_alarms", {}) is None


def test_hooks_disabled_skips_deny(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "agent_tool_hooks_enabled", False)
    monkeypatch.setattr(settings, "agent_tool_hook_deny_tools", "download_file")
    reset_tool_hooks()
    assert run_before_tool_hooks("download_file", {}) is None


def test_audit_after_hook_writes(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "agent_tool_hooks_enabled", True)
    configure_tool_hooks(CompositeToolHook([AuditToolHook(audit_after=True)]))
    append = MagicMock()
    with patch("app.services.audit_store.audit_store") as store:
        store.append = append
        run_after_tool_hooks(
            "query_alarms",
            {"limit": 1},
            '{"ok":true}',
            context=ToolExecutionContext(thread_id="t-after", principal_id="u1"),
        )
    append.assert_called_once()
    assert append.call_args.kwargs["event_type"] == "tool_hook_after"


@pytest.mark.asyncio
async def test_pipeline_prepare_applies_before_hooks(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "agent_tool_hooks_enabled", True)
    configure_tool_hooks(CompositeToolHook([DenyListToolHook(frozenset({"send_device_cmd"}))]))

    policy = MagicMock()
    policy.authorize.return_value = MagicMock(allowed=True, code="", reason="")
    pipeline = ToolExecutionPipeline(policy)

    def _fake_preflight(tool_name: str, args: dict):
        from contracts.tool_preflight import PreflightResult

        return PreflightResult(args=dict(args), interrupt=None)

    with patch("contracts.tool_preflight.preflight_tool", side_effect=_fake_preflight):
        prepared = await pipeline.prepare(
            ToolExecutionRequest(
                tool_name="send_device_cmd",
                args={"device_name": "x", "action": "开门"},
                context=ToolExecutionContext(
                    auth_token="Bearer t",
                    thread_id="t-pipe",
                    principal_id="u1",
                ),
            )
        )

    assert prepared.ready is False
    assert prepared.denied_result is not None
    assert "send_device_cmd" in (prepared.denied_result or "")


def test_tool_hook_decision_helpers():
    assert ToolHookDecision.allow().allowed is True
    d = ToolHookDecision.deny("nope", code="x")
    assert d.allowed is False
    assert d.code == "x"
