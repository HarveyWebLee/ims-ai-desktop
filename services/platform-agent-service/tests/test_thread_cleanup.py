"""thread_cleanup 单测（内存 Checkpointer）"""

from __future__ import annotations

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from app.persistence.bootstrap import get_checkpointer, init_persistence
from app.services.audit_store import audit_store
from app.services.thread_cleanup import delete_thread_persistence
from app.services.trace_store import trace_store


@pytest.mark.asyncio
async def test_delete_thread_persistence_clears_memory_stores():
    await init_persistence(None)

    thread_id = "thread-cleanup-test"
    saver = get_checkpointer()
    assert isinstance(saver, InMemorySaver)

    saver.storage[thread_id] = {"": {"cp-1": (("json", b"{}"), ("json", b"{}"), None)}}
    saver.writes[(thread_id, "", "cp-1")] = {}
    saver.blobs[(thread_id, "", "messages", 1)] = ("json", b"[]")

    trace_store.save_run(
        {
            "thread_id": thread_id,
            "run_id": "run-1",
            "events": [],
            "started_at": 1,
            "ended_at": 2,
        }
    )
    audit_store.append(
        thread_id=thread_id,
        user_id="u1",
        event_type="tool_start",
        run_id="run-1",
        tool_name="query_alarms",
    )

    await delete_thread_persistence(thread_id)

    assert thread_id not in saver.storage
    assert not trace_store.list_runs(thread_id)
    assert not audit_store.list_by_thread(thread_id)
