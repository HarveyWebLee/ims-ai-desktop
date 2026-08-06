"""线程工具子集仓储：内存主缓存与可选 Postgres 双写（供 resume 跨重启复用）。"""

from __future__ import annotations

import json
from typing import Any

_thread_tool_names: dict[str, frozenset[str]] = {}
_tool_subset_pool: Any | None = None


def configure_tool_subset_persistence(pool: Any | None) -> None:
    """注入工具子集使用的 Postgres 连接池；pool=None 时仅内存。"""
    global _tool_subset_pool, _thread_tool_names
    _tool_subset_pool = pool
    if pool is None:
        _thread_tool_names.clear()


def _db_write(thread_id: str, tool_names: frozenset[str] | None) -> None:
    """写入或清空工具子集。"""
    if _tool_subset_pool is None:
        return

    with _tool_subset_pool.connection() as conn:
        if tool_names is None:
            conn.execute(
                "DELETE FROM agent_thread_tool_subset WHERE thread_id = %s",
                (thread_id,),
            )
            return
        exists = conn.execute(
            "SELECT 1 FROM agent_sessions WHERE thread_id = %s LIMIT 1",
            (thread_id,),
        ).fetchone()
        if not exists:
            return
        payload = sorted(tool_names)
        conn.execute(
            """
            INSERT INTO agent_thread_tool_subset (thread_id, tool_names, updated_at)
            VALUES (%s, %s::jsonb, NOW())
            ON CONFLICT (thread_id) DO UPDATE SET
                tool_names = EXCLUDED.tool_names,
                updated_at = NOW()
            """,
            (thread_id, json.dumps(payload, ensure_ascii=False)),
        )


def _db_load(thread_id: str) -> frozenset[str] | None:
    """从 Postgres 加载工具子集。"""
    if _tool_subset_pool is None:
        return None
    with _tool_subset_pool.connection() as conn:
        row = conn.execute(
            "SELECT tool_names FROM agent_thread_tool_subset WHERE thread_id = %s",
            (thread_id,),
        ).fetchone()
    if not row:
        return None
    raw = row.get("tool_names") if isinstance(row, dict) else None
    if isinstance(raw, list):
        names = {str(n).strip() for n in raw if str(n).strip()}
        return frozenset(names) if names else frozenset()
    return None


def remember_thread_tool_subset(thread_id: str, tool_names: frozenset[str]) -> None:
    """记录本 thread 最近一次 chat 的工具子集（内存 + 可选 Postgres）。"""
    tid = (thread_id or "").strip()
    if not tid:
        return
    names = frozenset(tool_names)
    _thread_tool_names[tid] = names
    _db_write(tid, names)


def get_remembered_thread_tool_subset(thread_id: str) -> frozenset[str] | None:
    """读取 resume 应复用的工具子集；内存未命中时回源 Postgres。"""
    tid = (thread_id or "").strip()
    if not tid:
        return None
    cached = _thread_tool_names.get(tid)
    if cached is not None:
        return cached
    loaded = _db_load(tid)
    if loaded is not None:
        _thread_tool_names[tid] = loaded
    return loaded


def clear_thread_tool_subset(thread_id: str) -> None:
    """清除线程工具子集的内存与 Postgres 状态。"""
    tid = (thread_id or "").strip()
    if not tid:
        return
    _thread_tool_names.pop(tid, None)
    _db_write(tid, None)
