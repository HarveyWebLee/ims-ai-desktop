"""工具执行管线：preflight 期间须注入 JWT ContextVar。"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.application.tool_execution import ToolExecutionPipeline
from app.domain.tool_execution import ToolExecutionContext, ToolExecutionRequest
from contracts.context import current_auth_token


@pytest.mark.asyncio
async def test_prepare_sets_auth_contextvar_during_preflight():
    """send_device_cmd preflight 调平台时，须能读到 request 上下文中的 JWT。"""
    seen: dict[str, str | None] = {"token": None}

    def _fake_preflight(tool_name: str, args: dict):
        seen["token"] = current_auth_token.get()
        from contracts.tool_preflight import PreflightResult

        return PreflightResult(args=dict(args), interrupt=None)

    policy = MagicMock()
    policy.authorize.return_value = MagicMock(allowed=True, code="", reason="")
    pipeline = ToolExecutionPipeline(policy)

    with patch(
        "contracts.tool_preflight.preflight_tool",
        side_effect=_fake_preflight,
    ):
        prepared = await pipeline.prepare(
            ToolExecutionRequest(
                tool_name="send_device_cmd",
                args={"device_name": "716门禁", "action": "开门"},
                context=ToolExecutionContext(auth_token="Bearer test-jwt"),
            )
        )

    assert prepared.interrupt is None
    assert seen["token"] == "Bearer test-jwt"
    # prepare 结束后应还原，避免污染后续请求
    assert current_auth_token.get() is None
