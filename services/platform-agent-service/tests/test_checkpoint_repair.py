"""checkpoint 未完成 tool_calls 修复测试（异步 aget_state / aupdate_state）。"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.graph.checkpoint_utils import repair_dangling_tool_calls


@pytest.mark.asyncio
async def test_repair_dangling_tool_calls_appends_cancel_tool_messages():
    """AIMessage 有 tool_calls 但无 ToolMessage 时应补写取消结果。"""
    ai_msg = AIMessage(
        content="",
        tool_calls=[
            {
                "id": "call-abc",
                "name": "query_devices",
                "args": {"search": "门禁"},
            }
        ],
    )
    snap = MagicMock()
    snap.values = {"messages": [HumanMessage(content="查设备"), ai_msg]}

    agent = MagicMock()
    agent.aget_state = AsyncMock(return_value=snap)
    agent.aupdate_state = AsyncMock()

    with patch("app.graph.agent_factory.get_parent_graph", return_value=agent):
        count = await repair_dangling_tool_calls("thread-repair-1", "qwen3-32b")

    assert count == 1
    agent.aupdate_state.assert_awaited_once()
    config, payload = agent.aupdate_state.call_args[0]
    assert config == {"configurable": {"thread_id": "thread-repair-1"}}
    repairs = payload["messages"]
    assert len(repairs) == 1
    assert isinstance(repairs[0], ToolMessage)
    assert repairs[0].tool_call_id == "call-abc"
    assert repairs[0].name == "query_devices"
    assert "user_cancelled" in str(repairs[0].content)


@pytest.mark.asyncio
async def test_repair_dangling_tool_calls_skips_when_already_answered():
    """已有 ToolMessage 时不重复补写。"""
    ai_msg = AIMessage(
        content="",
        tool_calls=[
            {
                "id": "call-abc",
                "name": "query_devices",
                "args": {"search": "门禁"},
            }
        ],
    )
    tool_msg = ToolMessage(
        content='{"ok": true}',
        tool_call_id="call-abc",
        name="query_devices",
    )
    snap = MagicMock()
    snap.values = {"messages": [HumanMessage(content="查设备"), ai_msg, tool_msg]}

    agent = MagicMock()
    agent.aget_state = AsyncMock(return_value=snap)
    agent.aupdate_state = AsyncMock()

    with patch("app.graph.agent_factory.get_parent_graph", return_value=agent):
        count = await repair_dangling_tool_calls("thread-repair-2", "qwen3-32b")

    assert count == 0
    agent.aupdate_state.assert_not_called()
