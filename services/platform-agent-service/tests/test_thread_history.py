"""thread_history 异步读取 checkpoint 单测"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.services.thread_history import (
    attach_pending_interrupt_to_ui,
    get_thread_ui_messages,
    read_checkpoint_messages,
)


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


def test_attach_pending_interrupt_to_ui_by_mid():
    ui = [
        {"role": "user", "mid": "m1", "blocks": [{"type": "text", "content": "开门"}]},
        {
            "role": "assistant",
            "mid": "m1",
            "blocks": [{"type": "text", "content": "已完成"}],
        },
        {"role": "user", "mid": "m2", "blocks": [{"type": "text", "content": "播广播"}]},
        {
            "role": "assistant",
            "mid": "m2",
            "blocks": [{"type": "tool_call", "tool": "send_device_cmd", "status": "done"}],
        },
    ]
    pending = {
        "type": "confirm",
        "tool": "send_device_cmd",
        "message": "确认播报",
        "mid": "m2",
    }
    out = attach_pending_interrupt_to_ui(ui, pending)
    assert out[3]["blocks"][-1]["type"] == "interrupt"
    assert out[3]["blocks"][-1]["payload"]["mid"] == "m2"
    assert all(b.get("type") != "interrupt" for b in out[1]["blocks"])
