"""checkpoint 图内 interrupt 清理测试。"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.application.conversation.resume import stream_resume


@pytest.mark.asyncio
async def test_stream_resume_reject_clears_checkpoint_without_tool_sse():
    """用户 reject 且 checkpoint 有 interrupt：静默 abandon + 仅取消文案，不续跑父图。"""
    thread_id = "reject-ckpt-test"
    events: list[tuple[str, dict]] = []

    with (
        patch(
            "app.graph.checkpoint_utils.agent_has_pending_interrupt",
            return_value=True,
        ),
        patch(
            "app.graph.checkpoint_utils.abandon_stale_checkpoint_interrupt",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_abandon,
        patch(
            "app.graph.stream_envelope.wrap_stream_with_plan_trace",
            side_effect=lambda inner, **kw: inner,
        ),
        patch(
            "app.services.session_store.get_user_messages",
            return_value=["导出近一天的报警"],
        ),
        patch("app.middleware.auth.get_current_user_id", new_callable=AsyncMock, return_value="u1"),
    ):
        async for evt in stream_resume(
            thread_id=thread_id,
            model_id="qwen3.5-35b-a3b",
            resume_value={"type": "reject", "approved": False},
            auth_token=None,
            user_id="u1",
        ):
            events.append(evt)

    mock_abandon.assert_awaited_once()
    names = [e[0] for e in events]
    assert "message" in names
    assert names[-1] == "done"
    assert "error" not in names
    assert "tool_start" not in names
    assert "plan" not in names
    text = next(p.get("delta", "") for n, p in events if n == "message")
    assert "已取消" in text
