"""
Postgres 连接池、Checkpointer 与应用表初始化

- 有 POSTGRES_DSN：同步池（会话/审计表）+ AsyncPostgresSaver（图状态）
- 无 DSN：InMemorySaver + 内存 Store
"""

from __future__ import annotations

import logging
from typing import Any, cast

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool, ConnectionPool

from app.persistence.schema import setup_app_tables
from app.services.audit_store import (
    InMemoryAuditStore,
    PostgresAuditStore,
    configure_audit_store,
)
from app.services.session_store import (
    InMemorySessionStore,
    PostgresSessionStore,
    configure_bpmn_persistence,
    configure_session_store,
)
from app.services.tool_subset import configure_tool_subset_persistence
from app.services.trace_store import (
    InMemoryTraceStore,
    PostgresTraceStore,
    configure_trace_store,
)
from app.services.voice.voiceprint.store_pg import (
    InMemoryProfileStore,
    PostgresProfileStore,
    configure_profile_store,
)
from app.services.voice.voiceprint.store_qdrant import (
    InMemoryVectorIndex,
    configure_vector_index,
)
from app.sync.entity_sync_status import configure_entity_sync_persistence

logger = logging.getLogger(__name__)

_pool: ConnectionPool | None = None
_async_pool: AsyncConnectionPool | None = None
_checkpointer: AsyncPostgresSaver | InMemorySaver | None = None
_session_store: InMemorySessionStore | PostgresSessionStore | None = None
_using_postgres = False


def is_postgres_enabled() -> bool:
    return _using_postgres


def get_sync_pool() -> ConnectionPool:
    """返回同步业务连接池；未启用 Postgres 时抛错。"""
    if _pool is None:
        raise RuntimeError("Postgres 同步连接池未初始化")
    return _pool


def get_checkpointer() -> AsyncPostgresSaver | InMemorySaver:
    if _checkpointer is None:
        raise RuntimeError("持久化未初始化，请在 FastAPI startup 调用 init_persistence")
    return _checkpointer


def get_session_store() -> InMemorySessionStore | PostgresSessionStore:
    if _session_store is None:
        raise RuntimeError("SessionStore 未初始化")
    return _session_store


async def init_persistence(postgres_dsn: str | None) -> dict[str, Any]:
    """
    异步初始化持久化：AsyncPostgresSaver + 同步业务表连接池。
    """
    global _pool, _async_pool, _checkpointer, _session_store, _using_postgres

    dsn = (postgres_dsn or "").strip()
    if not dsn:
        logger.warning("未配置 POSTGRES_DSN，使用内存 Checkpointer（重启后会话/线程状态丢失）")
        _checkpointer = InMemorySaver()
        _session_store = InMemorySessionStore()
        configure_session_store(_session_store)
        configure_bpmn_persistence(None)
        configure_tool_subset_persistence(None)
        configure_entity_sync_persistence(None)
        configure_trace_store(InMemoryTraceStore())
        configure_audit_store(InMemoryAuditStore())
        configure_profile_store(InMemoryProfileStore())
        configure_vector_index(InMemoryVectorIndex())
        _using_postgres = False
        return {"mode": "memory"}

    logger.info("初始化 AsyncPostgres Checkpointer: %s", _mask_dsn(dsn))

    _pool = ConnectionPool(
        dsn,
        min_size=1,
        max_size=10,
        kwargs={"autocommit": True, "row_factory": dict_row},
    )
    with _pool.connection() as conn:
        conn.execute("SELECT 1")
        setup_app_tables(conn)

    _async_pool = AsyncConnectionPool(
        conninfo=dsn,
        min_size=1,
        max_size=10,
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
        open=False,
    )
    await _async_pool.open()
    _checkpointer = AsyncPostgresSaver(cast(Any, _async_pool))
    await _checkpointer.setup()

    _session_store = PostgresSessionStore(_pool)
    configure_session_store(_session_store)
    configure_bpmn_persistence(_pool)
    configure_tool_subset_persistence(_pool)
    configure_entity_sync_persistence(_pool)
    configure_trace_store(PostgresTraceStore(_pool))
    configure_audit_store(PostgresAuditStore(_pool))
    configure_profile_store(PostgresProfileStore(_pool))
    configure_vector_index(None)  # 生产走 Qdrant；未配置时 get_vector_index 回退内存
    _using_postgres = True
    logger.info("Postgres 持久化就绪（AsyncPostgresSaver + 会话索引）")
    return {"mode": "postgres", "dsn": _mask_dsn(dsn), "checkpointer": "async"}


async def close_persistence() -> None:
    """关闭异步/同步连接池并重置全局状态。"""
    global _pool, _async_pool, _checkpointer, _session_store, _using_postgres
    if _async_pool is not None:
        await _async_pool.close()
    if _pool is not None:
        _pool.close()
    _async_pool = None
    _pool = None
    _checkpointer = None
    _session_store = None
    _using_postgres = False
    configure_bpmn_persistence(None)
    configure_tool_subset_persistence(None)
    configure_entity_sync_persistence(None)
    configure_session_store(InMemorySessionStore())
    configure_trace_store(InMemoryTraceStore())
    configure_audit_store(InMemoryAuditStore())
    configure_profile_store(InMemoryProfileStore())
    configure_vector_index(InMemoryVectorIndex())


def _mask_dsn(dsn: str) -> str:
    if "@" not in dsn:
        return dsn
    prefix, host_part = dsn.split("@", 1)
    if "://" in prefix and ":" in prefix.split("://", 1)[1]:
        scheme, creds = prefix.split("://", 1)
        user = creds.split(":", 1)[0]
        return f"{scheme}://{user}:***@{host_part}"
    return f"***@{host_part}"
