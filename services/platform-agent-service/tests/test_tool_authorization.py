"""工具执行授权策略与管线测试。"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from app.application.execution.tool_executor import execute_tool_invoke
from app.application.tool_execution import (
    authorize_tool_call,
    configure_tool_authorization_policy,
)
from app.domain.tool_authorization import CatalogRequiredPermissionsPolicy
from app.domain.tool_execution import (
    ToolAuthorizationDecision,
    ToolExecutionContext,
    ToolExecutionRequest,
)


class DenyToolPolicy:
    """测试策略：拒绝指定工具并记录归一化请求。"""

    def __init__(self, denied_tool: str) -> None:
        self.denied_tool = denied_tool
        self.requests: list[ToolExecutionRequest] = []

    def authorize(self, request: ToolExecutionRequest) -> ToolAuthorizationDecision:
        self.requests.append(request)
        if request.tool_name == self.denied_tool:
            return ToolAuthorizationDecision.deny(
                "当前用户无权查询设备",
                code="device_read_denied",
            )
        return ToolAuthorizationDecision.allow()


@pytest.mark.asyncio
async def test_denied_tool_emits_tool_result_without_invoking_handler():
    """授权拒绝仍闭合 tool_start/tool_end，但不得调用真实 handler。"""
    policy = DenyToolPolicy("query_devices")
    previous = configure_tool_authorization_policy(policy)
    events: list[tuple[str, dict[str, Any]]] = []
    try:
        with patch(
            "app.services.agent_tool_retry.invoke_tool_async",
            new_callable=AsyncMock,
        ) as mock_invoke:
            async for event in execute_tool_invoke(
                "query_devices",
                {"device_name": "一号泵"},
                auth_token="Bearer test",
                thread_id="thread-1",
            ):
                events.append(event)
    finally:
        configure_tool_authorization_policy(previous)

    assert [name for name, _ in events] == ["tool_start", "tool_end"]
    result = json.loads(events[-1][1]["result"])
    assert result["ok"] is False
    assert result["summary"] == "当前用户无权查询设备"
    assert result["data"]["error_code"] == "device_read_denied"
    mock_invoke.assert_not_called()
    assert policy.requests[0].context.thread_id == "thread-1"
    assert policy.requests[0].context.principal_id


def test_catalog_policy_denies_when_permissions_not_injected(monkeypatch):
    """默认 fail-closed：未注入 permissions 时拒绝含 required_permissions 的写工具。"""
    from app.config import settings

    monkeypatch.setattr(settings, "agent_tool_permission_fail_closed", True)
    policy = CatalogRequiredPermissionsPolicy()
    decision = policy.authorize(
        ToolExecutionRequest(
            tool_name="batch_confirm_alarms",
            args={},
            context=ToolExecutionContext(principal_id="user_x"),
        )
    )
    assert decision.allowed is False
    assert decision.code == "tool_permission_context_missing"


def test_catalog_policy_allows_when_fail_closed_disabled(monkeypatch):
    """联调开关关闭时，未注入 permissions 保持兼容放行。"""
    from app.config import settings

    monkeypatch.setattr(settings, "agent_tool_permission_fail_closed", False)
    policy = CatalogRequiredPermissionsPolicy()
    decision = policy.authorize(
        ToolExecutionRequest(
            tool_name="batch_confirm_alarms",
            args={},
            context=ToolExecutionContext(principal_id="user_x"),
        )
    )
    assert decision.allowed is True


def test_catalog_policy_denies_missing_required_permission():
    policy = CatalogRequiredPermissionsPolicy()
    decision = policy.authorize(
        ToolExecutionRequest(
            tool_name="batch_confirm_alarms",
            args={},
            context=ToolExecutionContext(
                principal_id="user_x",
                attributes={"permissions": ["alarm:read"]},
            ),
        )
    )
    assert decision.allowed is False
    assert "alarm:confirm" in decision.reason


def test_authorize_tool_call_uses_current_policy():
    previous = configure_tool_authorization_policy(DenyToolPolicy("send_device_cmd"))
    try:
        decision = authorize_tool_call("send_device_cmd", {"device_code": "D1"})
        assert decision.allowed is False
    finally:
        configure_tool_authorization_policy(previous)


def test_enrich_injects_permissions_from_jwt_when_present():
    """JWT 声明 permissions 时，enrich 应写入 attributes；无声明则不注入。"""
    import base64
    import json

    from app.application.tool_execution import enrich_tool_execution_context

    def _fake_jwt(claims: dict[str, Any]) -> str:
        header = base64.urlsafe_b64encode(b'{"alg":"none"}').decode().rstrip("=")
        payload = base64.urlsafe_b64encode(json.dumps(claims).encode("utf-8")).decode().rstrip("=")
        return f"Bearer {header}.{payload}.sig"

    with_perms = enrich_tool_execution_context(
        auth_token=_fake_jwt({"permissions": ["alarm:confirm", "alarm:read"]})
    )
    assert with_perms.attributes.get("permissions") == [
        "alarm:confirm",
        "alarm:read",
    ]

    without_perms = enrich_tool_execution_context(auth_token=_fake_jwt({"username": "alice"}))
    assert "permissions" not in without_perms.attributes
