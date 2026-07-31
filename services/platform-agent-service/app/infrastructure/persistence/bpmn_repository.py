"""BPMN 编排快照仓储：内存主缓存与可选 Postgres 双写。"""

from __future__ import annotations

import json
from typing import Any

_bpmn_snapshots: dict[str, dict[str, Any]] = {}
_bpmn_pool: Any | None = None


def configure_bpmn_persistence(pool: Any | None) -> None:
    """注入 BPMN 快照使用的 Postgres 连接池。"""
    global _bpmn_pool, _bpmn_snapshots
    _bpmn_pool = pool
    if pool is None:
        _bpmn_snapshots.clear()


def _bpmn_db_write(thread_id: str, snapshot: dict[str, Any] | None) -> None:
    """写入或清空 BPMN 快照。"""
    if _bpmn_pool is None:
        return

    with _bpmn_pool.connection() as conn:
        if snapshot is None:
            conn.execute(
                "DELETE FROM agent_thread_bpmn WHERE thread_id = %s",
                (thread_id,),
            )
        else:
            # 会话索引可能被并发删除，先确认主表记录存在以避免外键错误。
            exists = conn.execute(
                "SELECT 1 FROM agent_sessions WHERE thread_id = %s LIMIT 1",
                (thread_id,),
            ).fetchone()
            if not exists:
                return
            conn.execute(
                """
                INSERT INTO agent_thread_bpmn (thread_id, snapshot, updated_at)
                VALUES (%s, %s::jsonb, NOW())
                ON CONFLICT (thread_id) DO UPDATE SET
                    snapshot = EXCLUDED.snapshot,
                    updated_at = NOW()
                """,
                (thread_id, json.dumps(snapshot, ensure_ascii=False)),
            )


def _bpmn_db_load(thread_id: str) -> dict[str, Any] | None:
    """从 Postgres 加载 BPMN 快照。"""
    if _bpmn_pool is None:
        return None
    with _bpmn_pool.connection() as conn:
        row = conn.execute(
            "SELECT snapshot FROM agent_thread_bpmn WHERE thread_id = %s",
            (thread_id,),
        ).fetchone()
    if not row or not row.get("snapshot"):
        return None
    data = row["snapshot"]
    return dict(data) if isinstance(data, dict) else None


def set_thread_bpmn_snapshot(thread_id: str, snapshot: dict[str, Any]) -> None:
    """保存线程 BPMN 快照到内存并可选双写 Postgres。"""
    tid = (thread_id or "").strip()
    if not tid:
        return
    _bpmn_snapshots[tid] = dict(snapshot)
    _bpmn_db_write(tid, dict(snapshot))


def get_thread_bpmn_snapshot(thread_id: str) -> dict[str, Any] | None:
    """读取 BPMN 快照，内存未命中时回源并回填。"""
    tid = (thread_id or "").strip()
    if not tid:
        return None
    data = _bpmn_snapshots.get(tid)
    if data is None:
        data = _bpmn_db_load(tid)
        if data is not None:
            _bpmn_snapshots[tid] = data
    return dict(data) if data else None


def clear_thread_bpmn_snapshot(thread_id: str) -> None:
    """清除线程 BPMN 快照的内存与 Postgres 状态。"""
    tid = (thread_id or "").strip()
    if not tid:
        return
    _bpmn_snapshots.pop(tid, None)
    _bpmn_db_write(tid, None)
