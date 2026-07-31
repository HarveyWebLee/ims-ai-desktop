"""
删除会话时清理 LangGraph Checkpoint 与内存态 Trace/Audit。

文件职责
--------
在用户删除 thread 时，把「图状态 checkpoint」以及（内存模式下的）
Trace / Audit 一并清掉，避免侧栏删了会话但后端仍留着旧图进度。

在 Agent 流程中的位置
--------------------
会话删除链路的收尾：
  DELETE session API → session_store.delete_session
    → delete_thread_persistence(thread_id)
    → 清理 checkpoint_*（及内存 trace/audit）

如何被调用
----------
- sessions 删除接口 / 清理编排（需与 session_store 删除成对调用）

白话解释
--------
删聊天窗口时，不光撕掉侧栏标签（session_store），还要把「这轮对话跑到哪一步」
的存档（Checkpoint）也扔掉。Postgres 里业务表可由外键 CASCADE；
但 LangGraph 自己的 checkpoint 表要单独 DELETE。

Postgres 模式下 agent_sessions 删除会 CASCADE 业务表（trace/audit/user_messages），
但 LangGraph checkpoint_* 表独立，需显式按 thread_id 清理。
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool

from app.persistence.bootstrap import get_checkpointer, is_postgres_enabled
from app.services.audit_store import audit_store
from app.services.trace_store import trace_store

logger = logging.getLogger(__name__)

# LangGraph PostgresSaver 使用的表（与 checkpoint/postgres/base.py MIGRATIONS 一致）
# 删除顺序从「写依赖」到「主表」，避免残留分片数据
_CHECKPOINT_TABLES = (
    "checkpoint_writes",
    "checkpoint_blobs",
    "checkpoints",
)


def _delete_postgres_checkpoints(thread_id: str, conn: Any) -> None:
    """按 thread_id 删除 LangGraph checkpoint 相关行。"""
    for table in _CHECKPOINT_TABLES:
        conn.execute(f"DELETE FROM {table} WHERE thread_id = %s", (thread_id,))


def _delete_memory_checkpoints(checkpointer: InMemorySaver, thread_id: str) -> None:
    """
    从 InMemorySaver 移除指定 thread 的全部 checkpoint 数据。

    InMemorySaver 内部用多个 dict（storage / writes / blobs），须逐一按 key 清理。
    """
    checkpointer.storage.pop(thread_id, None)

    write_keys = [key for key in checkpointer.writes if key[0] == thread_id]
    for key in write_keys:
        checkpointer.writes.pop(key, None)

    blob_keys = [key for key in checkpointer.blobs if key[0] == thread_id]
    for key in blob_keys:
        checkpointer.blobs.pop(key, None)


def delete_thread_persistence(thread_id: str) -> None:
    """
    删除 thread 关联的 Checkpoint；内存模式下同步清理 Trace/Audit。

    参数:
        thread_id: 会话线程 ID

    说明:
        - Postgres：checkpoint_* 表显式 DELETE；trace/audit 由 agent_sessions CASCADE
        - Memory：checkpoint + trace_store + audit_store 一并清理

    异常:
        checkpoint 清理失败会记录日志并向上抛出，避免静默残留。
    """
    tid = (thread_id or "").strip()
    if not tid:
        return

    checkpointer = get_checkpointer()

    try:
        if isinstance(checkpointer, PostgresSaver):
            conn_holder = checkpointer.conn
            if isinstance(conn_holder, ConnectionPool):
                with conn_holder.connection() as conn:
                    _delete_postgres_checkpoints(tid, conn)
            else:
                _delete_postgres_checkpoints(tid, conn_holder)
        elif isinstance(checkpointer, InMemorySaver):
            _delete_memory_checkpoints(checkpointer, tid)
        else:
            logger.warning(
                "未知 Checkpointer 类型，跳过 checkpoint 清理: %s",
                type(checkpointer).__name__,
            )
    except Exception:
        logger.exception("清理 checkpoint 失败: thread_id=%s", tid)
        raise

    # Postgres 业务表靠 CASCADE；仅内存模式需要手动删 Trace/Audit
    if not is_postgres_enabled():
        trace_store.delete_thread(tid)
        audit_store.delete_thread(tid)

    logger.info("已清理 thread 持久化数据: thread_id=%s", tid)
