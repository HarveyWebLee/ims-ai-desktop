"""thread_history 异步读取 checkpoint 单测"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.services.thread_history import (
    attach_pending_interrupt_to_ui,
    checkpoint_messages_to_ui,
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


def test_checkpoint_messages_to_ui_merges_same_mid_react_turn():
    """ReAct 多 AIMessage 同 mid 合并为一张助手卡（对齐实时 SSE）。"""
    mid = "turn-export"
    human = HumanMessage(
        content="查询并导出最近三天告警",
        id=mid,
        additional_kwargs={"mid": mid},
    )
    ai_tools = AIMessage(
        content="",
        id="ai-1",
        tool_calls=[
            {
                "id": "tc-query",
                "name": "query_alarms",
                "args": {"start_time": "近三天"},
            },
            {
                "id": "tc-export",
                "name": "export_alarms",
                "args": {},
            },
        ],
    )
    tool_q = ToolMessage(
        content='{"ok": true, "summary": "441"}',
        tool_call_id="tc-query",
        name="query_alarms",
    )
    tool_e = ToolMessage(
        content='{"ok": true, "summary": "exported"}',
        tool_call_id="tc-export",
        name="export_alarms",
    )
    ai_final = AIMessage(content="已为您查询到最近三天共 441 条告警，并已启动导出。", id="ai-2")

    ui = checkpoint_messages_to_ui([human, ai_tools, tool_q, tool_e, ai_final])
    assert len(ui) == 2
    assert ui[0]["role"] == "user"
    assert ui[0]["mid"] == mid
    assert ui[1]["role"] == "assistant"
    assert ui[1]["mid"] == mid
    types = [b["type"] for b in ui[1]["blocks"]]
    assert types.count("tool_call") == 2
    assert types.count("text") == 1
    assert ui[1]["blocks"][-1]["type"] == "text"
