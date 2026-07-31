"""thread_history 异步读取 checkpoint 单测"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.services.thread_history import get_thread_ui_messages, read_checkpoint_messages


@pytest.mark.asyncio
async def test_read_checkpoint_messages_uses_aget_not_sync_get():
    """主线程须走 aget，避免 AsyncPostgresSaver 同步 get 抛 InvalidStateError。"""
    messages = [
        HumanMessage(content="你好"),
        AIMessage(content="您好，有什么可以帮忙？"),
    ]
    saver = MagicMock()
    saver.aget = AsyncMock(
        return_value={"channel_values": {"messages": messages}},
    )
    saver.get = MagicMock(side_effect=AssertionError("禁止同步 get"))

    with patch("app.services.thread_history.get_checkpointer", return_value=saver):
        raw = await read_checkpoint_messages("thread-history-aget-test")
        ui = await get_thread_ui_messages("thread-history-aget-test")

    saver.aget.assert_awaited()
    saver.get.assert_not_called()
    assert len(raw) == 2
    assert ui == [
        {"role": "user", "blocks": [{"type": "text", "content": "你好"}]},
        {
            "role": "assistant",
            "blocks": [{"type": "text", "content": "您好，有什么可以帮忙？"}],
        },
    ]
