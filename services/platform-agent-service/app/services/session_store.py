"""会话持久化服务入口，聚合 StoreProxy、BPMN 与编排清理。"""

from __future__ import annotations

from app.infrastructure.persistence.bpmn_repository import (
    clear_thread_bpmn_snapshot,
    configure_bpmn_persistence,
    get_thread_bpmn_snapshot,
    set_thread_bpmn_snapshot,
)
from app.infrastructure.persistence.contracts import SessionStoreProtocol
from app.infrastructure.persistence.orchestration_cleanup import clear_thread_orchestration
from app.infrastructure.persistence.session_repository import (
    InMemorySessionStore,
    PostgresSessionStore,
)
from app.services.store_proxy import StoreProxy

__all__ = [
    "InMemorySessionStore",
    "PostgresSessionStore",
    "SessionStoreProtocol",
    "clear_thread_bpmn_snapshot",
    "clear_thread_orchestration",
    "configure_bpmn_persistence",
    "configure_session_store",
    "get_thread_bpmn_snapshot",
    "get_user_messages",
    "session_store",
    "set_thread_bpmn_snapshot",
]

session_store: SessionStoreProtocol = StoreProxy(InMemorySessionStore())  # type: ignore[assignment]


def configure_session_store(store: SessionStoreProtocol) -> None:
    """注入当前会话仓储实现，并保持代理对象身份稳定。"""
    if isinstance(session_store, StoreProxy):
        session_store.configure(store)
    else:
        raise RuntimeError("session_store 代理未初始化")


def get_user_messages(thread_id: str, limit: int = 8) -> list[str]:
    """通过当前会话仓储读取近期用户消息。"""
    return session_store.get_user_messages(thread_id, limit=limit)
