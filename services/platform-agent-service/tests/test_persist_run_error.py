"""checkpoint 运行错误落盘测试（SSE error → AIMessage）。"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.graph.checkpoint_utils import persist_run_error_message


@pytest.mark.asyncio
async def test_persist_run_error_message_appends_ai_message():
    snap = MagicMock()
    snap.values = {"messages": [HumanMessage(content="你好")]}

    agent = MagicMock()
    agent.aget_state = AsyncMock(return_value=snap)
    agent.aupdate_state = AsyncMock()

    payload = {
        "code": 50002,
        "message": "当前模型免费额度已用尽或账户未开通按量付费",
        "data": {"kind": "quota_exhausted", "hint": "请开通按量付费"},
    }

    with patch("app.graph.agent_factory.get_parent_graph", return_value=agent):
        ok = await persist_run_error_message("t-err", "qwen3.5-35b-a3b", payload, mid="mid-1")

    assert ok is True
    agent.aupdate_state.assert_awaited_once()
    _config, update = agent.aupdate_state.call_args[0]
    msgs = update["messages"]
    assert len(msgs) == 1
    assert isinstance(msgs[0], AIMessage)
    assert "免费额度" in str(msgs[0].content)
    assert msgs[0].additional_kwargs.get("mid") == "mid-1"


@pytest.mark.asyncio
async def test_persist_run_error_message_skips_duplicate():
    existing = AIMessage(content="⚠️ 当前模型免费额度已用尽或账户未开通按量付费\n\n请开通按量付费")
    snap = MagicMock()
    snap.values = {"messages": [HumanMessage(content="你好"), existing]}

    agent = MagicMock()
    agent.aget_state = AsyncMock(return_value=snap)
    agent.aupdate_state = AsyncMock()

    payload = {
        "message": "当前模型免费额度已用尽或账户未开通按量付费",
        "data": {"hint": "请开通按量付费"},
    }

    with patch("app.graph.agent_factory.get_parent_graph", return_value=agent):
        ok = await persist_run_error_message("t-err", "qwen3.5-35b-a3b", payload)

    assert ok is True
    agent.aupdate_state.assert_not_called()
