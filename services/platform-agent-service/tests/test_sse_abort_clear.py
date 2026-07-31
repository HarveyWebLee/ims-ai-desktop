"""SSE abort / 断开时清理编排暂存（BPMN 快照 + execution_state）。"""

from __future__ import annotations

import asyncio

import pytest

from app.api.chat import _clear_thread_orchestration_on_abort, _sse_from_stream
from app.services.bpmn_execution_state import (
    clear_bpmn_execution_state,
    get_bpmn_execution_state,
    set_bpmn_execution_state,
)
from app.services.session_store import (
    clear_thread_orchestration,
    get_thread_bpmn_snapshot,
    set_thread_bpmn_snapshot,
)


def test_clear_thread_orchestration_on_abort_removes_bpmn_and_exec_state():
    tid = "thread-abort-clear"
    clear_thread_orchestration(tid)
    set_thread_bpmn_snapshot(tid, {"steps": [{"tool": "query_alarms"}]})
    set_bpmn_execution_state(tid, {"paused_node_id": "step_open"})
    assert get_thread_bpmn_snapshot(tid) is not None
    assert get_bpmn_execution_state(tid) is not None

    _clear_thread_orchestration_on_abort(tid, reason="cancelled")
    assert get_thread_bpmn_snapshot(tid) is None
    assert get_bpmn_execution_state(tid) is None


@pytest.mark.asyncio
async def test_sse_cancelled_error_clears_bpmn():
    tid = "thread-sse-cancel"
    clear_thread_orchestration(tid)
    set_thread_bpmn_snapshot(tid, {"steps": [{"tool": "download_file"}]})
    set_bpmn_execution_state(tid, {"paused_node_id": "n1"})

    async def failing_stream():
        yield ("message", {"type": "text", "delta": "hi"})
        raise asyncio.CancelledError()

    response = await _sse_from_stream(failing_stream(), thread_id=tid)
    with pytest.raises(asyncio.CancelledError):
        async for _ in response.body_iterator:
            pass

    assert get_thread_bpmn_snapshot(tid) is None
    assert get_bpmn_execution_state(tid) is None


@pytest.mark.asyncio
async def test_sse_client_disconnect_clears_bpmn():
    tid = "thread-sse-disconnect"
    clear_thread_orchestration(tid)
    set_thread_bpmn_snapshot(tid, {"steps": [{"tool": "get_device_detail"}]})
    set_bpmn_execution_state(tid, {"paused_node_id": "step_query"})

    async def failing_stream():
        yield ("message", {"type": "text", "delta": "hi"})
        raise ConnectionResetError("Connection reset by peer")

    response = await _sse_from_stream(failing_stream(), thread_id=tid)
    with pytest.raises(ConnectionResetError):
        async for _ in response.body_iterator:
            pass

    assert get_thread_bpmn_snapshot(tid) is None
    assert get_bpmn_execution_state(tid) is None
    clear_bpmn_execution_state(tid)
