"""
审计日志持久化服务：Postgres 或内存回退。

文件职责
--------
记录 Agent 运行过程中的关键 SSE 事件（工具调用、Re-plan、中断、错误），
供合规审计与问题排查。与 Trace 模块互补：Trace 面向开发者调试面板，
Audit 面向业务审计（含用户 ID、脱敏后的 payload）。

在 Agent 流程中的位置
--------------------
    SSE 事件产出（tool_start / tool_end / replan / interrupt / error）
      → build_audit_from_sse 映射并脱敏
      → audit_store.append(...)
    查询：GET 审计相关 API → list_by_thread
    删会话：thread 清理 → delete_thread

如何被调用
----------
- 启动：``persistence.bootstrap`` → ``configure_audit_store(Postgres|Memory)``
- 运行时：流包装层对关键事件写审计；业务代码通过模块级 ``audit_store`` 访问
- 全局实例用 ``StoreProxy``，避免「启动前被 import 的旧引用」指不到新实现

存储实现
--------
- InMemoryAuditStore：开发 / 无 Postgres；重启丢失，每 thread 最多 200 条
- PostgresAuditStore：表 ``agent_audit_logs``
"""

from __future__ import annotations

# ── 标准库 ──
import json
import logging
from datetime import UTC, datetime
from typing import Any, Protocol, cast  # Protocol 定义「结构类型」接口，类似 TS interface

# ── 第三方 ──
from psycopg_pool import ConnectionPool  # PostgreSQL 连接池

from app.services.store_proxy import StoreProxy
from app.utils.psycopg_rows import as_dict_row

logger = logging.getLogger(__name__)

# 需写入审计的关键事件（与 Trace 对齐，每条业务事件一条记录）
# frozenset：不可变集合，元素必须可哈希
AUDIT_SSE_EVENTS = frozenset(
    {
        "tool_start",
        "tool_end",
        "replan",
        "interrupt",
        "error",
    }
)


def mask_payload_summary(payload: dict[str, Any] | None) -> dict[str, Any]:
    """
    敏感字段脱敏后供审计存储。

    参数:
        payload: 原始事件 payload

    返回:
        脱敏后的 dict 副本（password/token 等替换为 ***，超长字符串截断）
    """
    if not payload:
        return {}
    masked: dict[str, Any] = {}
    for key, value in payload.items():
        lower = key.lower()
        if any(s in lower for s in ("password", "token", "secret", "authorization")):
            masked[key] = "***"
        elif isinstance(value, str) and len(value) > 500:
            masked[key] = value[:500] + "…"
        else:
            masked[key] = value
    return masked


def build_audit_from_sse(
    event_name: str, payload: dict[str, Any]
) -> tuple[str, str | None, dict[str, Any]] | None:
    """
    将 SSE 事件映射为审计字段。

    参数:
        event_name: SSE 事件名，如 "tool_start"
        payload: 事件数据 dict

    返回:
        (event_type, tool_name, payload_summary) 三元组；非关键事件返回 None
    """
    if event_name not in AUDIT_SSE_EVENTS:
        return None

    tool_name = str(payload.get("tool") or "") or None

    if event_name == "tool_start":
        return (
            "tool_start",
            tool_name,
            mask_payload_summary({"tool": tool_name, "args": payload.get("args")}),
        )
    if event_name == "tool_end":
        result = str(payload.get("result", ""))[:200]
        return (
            "tool_end",
            tool_name,
            mask_payload_summary({"tool": tool_name, "result_preview": result}),
        )
    if event_name == "replan":
        return (
            "replan",
            tool_name or str(payload.get("failed_tool") or "") or None,
            mask_payload_summary(payload),
        )
    if event_name == "interrupt":
        return ("interrupt", tool_name, mask_payload_summary(payload))
    if event_name == "error":
        return ("error", tool_name, mask_payload_summary(payload))
    return None


class AuditStoreProtocol(Protocol):
    """
    审计存储接口（Protocol：结构类型，类似 TypeScript interface）。

    凡实现了下列三个方法的类，均可注入为 ``audit_store`` 后端。
    """

    def append(
        self,
        *,
        thread_id: str,
        user_id: str,
        event_type: str,
        run_id: str | None = None,
        tool_name: str | None = None,
        payload_summary: dict[str, Any] | None = None,
    ) -> None:
        """追加一条审计记录（应已脱敏）。"""
        ...

    def list_by_thread(
        self,
        thread_id: str,
        *,
        limit: int = 100,
        run_id: str | None = None,
        event_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """按 thread 查询审计记录，最新在前；可按 run_id / event_type 筛选。"""
        ...

    def delete_thread(self, thread_id: str) -> None:
        """删除某会话 thread 下全部审计记录（清理会话时调用）。"""
        ...


def _filter_audit_entries(
    entries: list[dict[str, Any]],
    *,
    run_id: str | None,
    event_type: str | None,
) -> list[dict[str, Any]]:
    """按 run_id / event_type 过滤审计记录。"""
    filtered = entries
    if run_id:
        filtered = [e for e in filtered if str(e.get("run_id") or "") == run_id]
    if event_type:
        filtered = [e for e in filtered if str(e.get("event_type") or "") == event_type]
    return filtered


class InMemoryAuditStore:
    """
    内存审计存储（开发/测试用）。

    数据保存在进程内存 dict 中，重启后丢失；每个 thread 最多保留 200 条。
    """

    def __init__(self) -> None:
        # thread_id → 审计记录列表
        self._logs: dict[str, list[dict[str, Any]]] = {}

    def append(
        self,
        *,
        thread_id: str,
        user_id: str,
        event_type: str,
        run_id: str | None = None,
        tool_name: str | None = None,
        payload_summary: dict[str, Any] | None = None,
    ) -> None:
        """追加一条审计记录到内存列表头部。"""
        entry = _make_entry(
            thread_id=thread_id,
            user_id=user_id,
            event_type=event_type,
            run_id=run_id,
            tool_name=tool_name,
            payload_summary=payload_summary,
        )
        self._logs.setdefault(thread_id, []).insert(0, entry)  # 新记录插到最前
        self._logs[thread_id] = self._logs[thread_id][:200]  # 截断保留最新 200 条

    def list_by_thread(
        self,
        thread_id: str,
        *,
        limit: int = 100,
        run_id: str | None = None,
        event_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """查询某 thread 的审计记录（最新在前），支持 run / event_type 筛选。"""
        rows = list(self._logs.get(thread_id, []))
        rows = _filter_audit_entries(rows, run_id=run_id, event_type=event_type)
        return rows[:limit]

    def delete_thread(self, thread_id: str) -> None:
        """删除某 thread 的全部审计记录（内存模式）。"""
        self._logs.pop(thread_id, None)


class PostgresAuditStore:
    """
    PostgreSQL 审计存储（生产环境）。

    表: agent_audit_logs
    """

    def __init__(self, pool: ConnectionPool) -> None:
        self._pool = pool

    def append(
        self,
        *,
        thread_id: str,
        user_id: str,
        event_type: str,
        run_id: str | None = None,
        tool_name: str | None = None,
        payload_summary: dict[str, Any] | None = None,
    ) -> None:
        """INSERT 一条审计记录到 Postgres。"""
        summary = payload_summary or {}
        # with 语句自动管理连接借还
        with self._pool.connection() as conn:
            conn.execute(
                """
                INSERT INTO agent_audit_logs
                    (thread_id, run_id, user_id, event_type, tool_name, payload_summary)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                """,
                (
                    thread_id,
                    run_id,
                    user_id,
                    event_type,
                    tool_name,
                    json.dumps(summary, ensure_ascii=False),
                ),
            )

    def list_by_thread(
        self,
        thread_id: str,
        *,
        limit: int = 100,
        run_id: str | None = None,
        event_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """从 Postgres 查询某 thread 的审计记录。"""
        clauses = ["thread_id = %s"]
        params: list[Any] = [thread_id]
        if run_id:
            clauses.append("run_id = %s")
            params.append(run_id)
        if event_type:
            clauses.append("event_type = %s")
            params.append(event_type)
        params.append(limit)
        where = " AND ".join(clauses)
        with self._pool.connection() as conn:
            rows = conn.execute(
                cast(
                    Any,
                    f"""
                SELECT id, thread_id, run_id, user_id, event_type, tool_name,
                       payload_summary, created_at
                FROM agent_audit_logs
                WHERE {where}
                ORDER BY created_at DESC
                LIMIT %s
                """,
                ),
                tuple(params),
            ).fetchall()
        return [_row_to_entry(as_dict_row(row)) for row in rows]

    def delete_thread(self, thread_id: str) -> None:
        """删除某 thread 的审计记录（Postgres 通常由 agent_sessions CASCADE）。"""
        with self._pool.connection() as conn:
            conn.execute(
                "DELETE FROM agent_audit_logs WHERE thread_id = %s",
                (thread_id,),
            )


def _make_entry(
    *,
    thread_id: str,
    user_id: str,
    event_type: str,
    run_id: str | None,
    tool_name: str | None,
    payload_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    """构造一条内存审计记录 dict（与 DB 行结构对齐）。"""
    return {
        "id": None,
        "thread_id": thread_id,
        "run_id": run_id,
        "user_id": user_id,
        "event_type": event_type,
        "tool_name": tool_name,
        "payload_summary": payload_summary or {},
        "created_at": datetime.now(UTC).isoformat(),
    }


def _row_to_entry(row: dict[str, Any]) -> dict[str, Any]:
    """将 Postgres 查询行转为前端/API 友好的 dict。"""
    created = row.get("created_at")
    if isinstance(created, datetime):
        created_at = created.astimezone(UTC).isoformat()
    else:
        created_at = str(created) if created else None
    return {
        "id": row.get("id"),
        "thread_id": row["thread_id"],
        "run_id": row.get("run_id"),
        "user_id": row["user_id"],
        "event_type": row["event_type"],
        "tool_name": row.get("tool_name"),
        "payload_summary": row.get("payload_summary") or {},
        "created_at": created_at,
    }


# 模块级代理：避免 startup configure 后旧 import 仍指向 InMemory 实现
audit_store: AuditStoreProtocol = StoreProxy(InMemoryAuditStore())  # type: ignore[assignment]


def configure_audit_store(store: AuditStoreProtocol) -> None:
    """
    由 persistence.bootstrap 在应用启动时注入 Postgres 或内存实现。

    参数:
        store: 符合 AuditStoreProtocol 的存储实例
    """
    if isinstance(audit_store, StoreProxy):
        audit_store.configure(store)
    else:
        raise RuntimeError("audit_store 代理未初始化")
