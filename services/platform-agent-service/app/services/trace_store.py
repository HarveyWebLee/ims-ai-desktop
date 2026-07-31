"""
Trace 持久化服务：Postgres 或内存回退。

文件职责
--------
把 TraceCollector.export() 打好的「一场 run 短片」存起来，并提供按 thread / run_id 查询。

一次 run 的链路（白话）
----------------------
  TraceCollector 拍完 → export() 得到 {thread_id, run_id, events, started_at, ended_at}
    → trace_store.save_run（入库）
  用户打开 Trace 面板 → list_runs / get_run →（API 层再 enrich_trace_graph）

注意: 这里只管「存取」；构图在 trace_graph，采集在 trace_collector。

在 Agent 流程中的位置
--------------------
持久化层；与 audit_store 并列，经 StoreProxy 在启动时切换实现。

如何被调用
----------
- 流结束：``trace_store.save_run(collector.export())``
- Trace API：``list_runs`` / ``get_run``
- 删会话（内存模式）：``thread_cleanup`` → ``delete_thread``

表结构（Postgres）:
    agent_thread_traces(thread_id, run_id, events, started_at, ended_at)

全局实例:
    trace_store — configure_trace_store() 在启动时替换内部实现
"""

from __future__ import annotations

# ── 标准库 ──
import json
import logging
from datetime import UTC, datetime
from typing import Any, Protocol

# ── 第三方 ──
from psycopg_pool import ConnectionPool

from app.services.store_proxy import StoreProxy
from app.utils.psycopg_rows import as_dict_row

logger = logging.getLogger(__name__)


class TraceStoreProtocol(Protocol):
    """
    Trace 存储接口（内存 / Postgres 同契约）。
    """

    def save_run(self, trace: dict[str, Any]) -> None:
        """保存或 UPSERT 一轮 run（同 thread_id+run_id 覆盖 events/ended_at）。"""
        ...

    def list_runs(self, thread_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
        """列出某 thread 的历史 run（通常最新在前）。"""
        ...

    def get_run(self, thread_id: str, run_id: str) -> dict[str, Any] | None:
        """按 run_id 获取单条完整 trace；不存在返回 None。"""
        ...

    def delete_thread(self, thread_id: str) -> None:
        """删除某 thread 下全部 run（内存模式删会话时用；PG 常靠 CASCADE）。"""
        ...


class InMemoryTraceStore:
    """
    内存 Trace 存储（开发/无 Postgres 时使用）。

    每个 thread 最多保留 50 轮 run。
    """

    def __init__(self) -> None:
        self._runs: dict[str, list[dict[str, Any]]] = {}

    def save_run(self, trace: dict[str, Any]) -> None:
        """
        保存一轮 trace 到内存（新 run 插到列表头部）。

        参数:
            trace: TraceCollector.export() 返回值
        """
        tid = trace.get("thread_id", "")
        self._runs.setdefault(tid, []).insert(0, trace)
        self._runs[tid] = self._runs[tid][:50]

    def list_runs(self, thread_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
        """列出某 thread 的历史 run（最新在前）。"""
        return list(self._runs.get(thread_id, [])[:limit])

    def get_run(self, thread_id: str, run_id: str) -> dict[str, Any] | None:
        """按 run_id 查找单条 trace。"""
        for run in self._runs.get(thread_id, []):
            if run.get("run_id") == run_id:
                return run
        return None

    def delete_thread(self, thread_id: str) -> None:
        """删除某 thread 的全部 trace（内存模式）。"""
        self._runs.pop(thread_id, None)


class PostgresTraceStore:
    """
    PostgreSQL Trace 存储（生产环境）。

    使用 UPSERT：同 thread_id + run_id 冲突时更新 events 和 ended_at。
    """

    def __init__(self, pool: ConnectionPool) -> None:
        self._pool = pool

    def save_run(self, trace: dict[str, Any]) -> None:
        """
        INSERT 或 UPDATE 一轮 trace。

        参数:
            trace: 含 thread_id、run_id、events、started_at、ended_at
        """
        with self._pool.connection() as conn:
            conn.execute(
                """
                INSERT INTO agent_thread_traces (thread_id, run_id, events, started_at, ended_at)
                VALUES (%s, %s, %s::jsonb, to_timestamp(%s / 1000.0), to_timestamp(%s / 1000.0))
                ON CONFLICT (thread_id, run_id) DO UPDATE SET
                    events = EXCLUDED.events,
                    ended_at = EXCLUDED.ended_at
                """,
                (
                    trace["thread_id"],
                    trace["run_id"],
                    json.dumps(trace.get("events") or [], ensure_ascii=False),
                    trace.get("started_at", 0),
                    trace.get("ended_at", 0),
                ),
            )

    def list_runs(self, thread_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
        """从 Postgres 查询某 thread 的历史 run。"""
        with self._pool.connection() as conn:
            rows = conn.execute(
                """
                SELECT run_id, events, started_at, ended_at
                FROM agent_thread_traces
                WHERE thread_id = %s
                ORDER BY started_at DESC
                LIMIT %s
                """,
                (thread_id, limit),
            ).fetchall()
        return [_row_to_run(thread_id, as_dict_row(row)) for row in rows]

    def get_run(self, thread_id: str, run_id: str) -> dict[str, Any] | None:
        """按 run_id 查询单条 trace。"""
        with self._pool.connection() as conn:
            row = conn.execute(
                """
                SELECT run_id, events, started_at, ended_at
                FROM agent_thread_traces
                WHERE thread_id = %s AND run_id = %s
                """,
                (thread_id, run_id),
            ).fetchone()
        if not row:
            return None
        return _row_to_run(thread_id, as_dict_row(row))

    def delete_thread(self, thread_id: str) -> None:
        """删除某 thread 的 trace（Postgres 通常由 agent_sessions CASCADE）。"""
        with self._pool.connection() as conn:
            conn.execute(
                "DELETE FROM agent_thread_traces WHERE thread_id = %s",
                (thread_id,),
            )


def _row_to_run(thread_id: str, row: dict[str, Any]) -> dict[str, Any]:
    """将 DB 行转为 API 友好的 trace dict。"""
    started = row.get("started_at")
    ended = row.get("ended_at")
    return {
        "thread_id": thread_id,
        "run_id": row["run_id"],
        "events": row.get("events") or [],
        "started_at": _ts_ms(started),
        "ended_at": _ts_ms(ended),
    }


def _ts_ms(value: Any) -> int:
    """
    将 datetime 或 None 转为毫秒时间戳。

    参数:
        value: Postgres 返回的 datetime 或 None

    返回:
        毫秒整数，无法转换时返回 0
    """
    if isinstance(value, datetime):
        return int(value.astimezone(UTC).timestamp() * 1000)
    return 0


# 模块级代理：避免 startup configure 后旧 import 仍指向 InMemory 实现
trace_store: TraceStoreProtocol = StoreProxy(InMemoryTraceStore())  # type: ignore[assignment]


def configure_trace_store(store: TraceStoreProtocol) -> None:
    """
    由 persistence.bootstrap 在启动时注入 Postgres 或内存实现。

    参数:
        store: 符合 TraceStoreProtocol 的实例
    """
    if isinstance(trace_store, StoreProxy):
        trace_store.configure(store)
    else:
        raise RuntimeError("trace_store 代理未初始化")
