"""Store 代理：确保 configure 后旧 import 仍指向当前实现。"""

import pytest

from app.api import chat
from app.persistence.bootstrap import init_persistence
from app.services.session_store import InMemorySessionStore, PostgresSessionStore, session_store
from app.services.store_proxy import StoreProxy


@pytest.mark.asyncio
async def test_session_store_proxy_survives_configure_after_import():
    """模拟 FastAPI：先 import chat，再 init_persistence，chat 应使用 Postgres。"""
    from app.persistence.bootstrap import close_persistence

    assert isinstance(session_store, StoreProxy)
    # chat 在模块加载时已 import session_store
    assert isinstance(chat.session_store, StoreProxy)
    assert chat.session_store is session_store

    # 未 configure 前为内存实现
    assert isinstance(session_store.inner, InMemorySessionStore)

    dsn = "postgresql://agent:agent@127.0.0.1:16543/platform_agent"
    try:
        info = await init_persistence(dsn)
    except Exception as exc:  # noqa: BLE001 — 本机无 Postgres 时跳过
        pytest.skip(f"Postgres 不可用，跳过代理切换断言: {exc}")

    try:
        assert info["mode"] == "postgres"
        assert isinstance(session_store.inner, PostgresSessionStore)
        assert isinstance(chat.session_store.inner, PostgresSessionStore)
        assert chat.session_store.inner is session_store.inner
    finally:
        await close_persistence()
        assert isinstance(session_store.inner, InMemorySessionStore)


def test_session_store_bpmn_snapshot_methods():
    """InMemorySessionStore 应代理 BPMN 快照读写。"""
    store = InMemorySessionStore()
    tid = "test-thread-bpmn"
    snapshot = {
        "steps": [{"id": "1", "tool": "query_alarms"}],
        "flow_document": {"nodes": [], "edges": []},
    }
    store.set_thread_bpmn_snapshot(tid, snapshot)
    loaded = store.get_thread_bpmn_snapshot(tid)
    assert loaded is not None
    assert loaded["steps"][0]["tool"] == "query_alarms"
    store.clear_thread_bpmn_snapshot(tid)
    assert store.get_thread_bpmn_snapshot(tid) is None
