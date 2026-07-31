"""会话索引与近期用户消息仓储。"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from psycopg_pool import ConnectionPool

from app.infrastructure.persistence.bpmn_repository import (
    clear_thread_bpmn_snapshot,
    get_thread_bpmn_snapshot,
    set_thread_bpmn_snapshot,
)
from app.infrastructure.persistence.orchestration_cleanup import clear_thread_orchestration
from app.utils.psycopg_rows import as_dict_row


class InMemorySessionStore:
    """在内存中维护会话索引与近期用户消息。"""

    def __init__(self) -> None:
        self._sessions: dict[str, list[dict[str, Any]]] = {}
        self._thread_user_messages: dict[str, list[str]] = {}

    def upsert_session(
        self,
        user_id: str,
        thread_id: str,
        title: str | None = None,
    ) -> None:
        """创建新会话或刷新已有会话。"""
        sessions = self._sessions.setdefault(user_id, [])
        now = datetime.now(UTC).isoformat()
        for session in sessions:
            if session["thread_id"] == thread_id:
                session["updated_at"] = now
                if title:
                    session["title"] = title
                return
        sessions.insert(
            0,
            {
                "thread_id": thread_id,
                "title": title or "新会话",
                "updated_at": now,
                "created_at": now,
            },
        )

    def list_sessions(self, user_id: str) -> list[dict[str, Any]]:
        """返回用户的会话列表。"""
        return self._sessions.get(user_id, [])

    def has_thread(self, user_id: str, thread_id: str) -> bool:
        """当前用户是否拥有指定会话。"""
        return any(session["thread_id"] == thread_id for session in self._sessions.get(user_id, []))

    def append_user_message(self, thread_id: str, message: str, *, limit: int = 8) -> None:
        """追加非空用户消息并保留最近 limit 条。"""
        text = (message or "").strip()
        if not text:
            return
        messages = self._thread_user_messages.setdefault(thread_id, [])
        messages.append(text)
        if len(messages) > limit:
            self._thread_user_messages[thread_id] = messages[-limit:]

    def get_user_messages(self, thread_id: str, limit: int = 8) -> list[str]:
        """获取近期用户消息，按时间正序返回。"""
        return list(self._thread_user_messages.get(thread_id, [])[-limit:])

    def delete_session(self, user_id: str, thread_id: str) -> bool:
        """删除会话与用户消息；成功后全清编排状态。"""
        sessions = self._sessions.get(user_id, [])
        next_sessions = [session for session in sessions if session["thread_id"] != thread_id]
        if len(next_sessions) == len(sessions):
            return False
        self._sessions[user_id] = next_sessions
        self._thread_user_messages.pop(thread_id, None)
        clear_thread_orchestration(thread_id)
        return True

    def set_thread_bpmn_snapshot(self, thread_id: str, snapshot: dict[str, Any]) -> None:
        """委托 BPMN 仓储保存快照。"""
        set_thread_bpmn_snapshot(thread_id, snapshot)

    def get_thread_bpmn_snapshot(self, thread_id: str) -> dict[str, Any] | None:
        """委托 BPMN 仓储读取快照。"""
        return get_thread_bpmn_snapshot(thread_id)

    def clear_thread_bpmn_snapshot(self, thread_id: str) -> None:
        """委托 BPMN 仓储清除快照。"""
        clear_thread_bpmn_snapshot(thread_id)


class PostgresSessionStore:
    """在 Postgres 中维护会话索引与近期用户消息。"""

    def __init__(self, pool: ConnectionPool) -> None:
        self._pool = pool

    def upsert_session(
        self,
        user_id: str,
        thread_id: str,
        title: str | None = None,
    ) -> None:
        """UPSERT 会话元数据。"""
        with self._pool.connection() as conn:
            conn.execute(
                """
                INSERT INTO agent_sessions (thread_id, user_id, title, created_at, updated_at)
                VALUES (%s, %s, %s, NOW(), NOW())
                ON CONFLICT (thread_id) DO UPDATE SET
                    user_id = EXCLUDED.user_id,
                    updated_at = NOW(),
                    title = COALESCE(EXCLUDED.title, agent_sessions.title)
                """,
                (thread_id, user_id, title or "新会话"),
            )

    def list_sessions(self, user_id: str) -> list[dict[str, Any]]:
        """按更新时间倒序查询用户会话。"""
        with self._pool.connection() as conn:
            rows = conn.execute(
                """
                SELECT thread_id, title, created_at, updated_at
                FROM agent_sessions
                WHERE user_id = %s
                ORDER BY updated_at DESC
                """,
                (user_id,),
            ).fetchall()
        return [
            {
                "thread_id": (entry := as_dict_row(row))["thread_id"],
                "title": entry["title"],
                "created_at": _iso(entry["created_at"]),
                "updated_at": _iso(entry["updated_at"]),
            }
            for row in rows
        ]

    def has_thread(self, user_id: str, thread_id: str) -> bool:
        """查询当前用户是否拥有指定会话。"""
        with self._pool.connection() as conn:
            row = conn.execute(
                """
                SELECT 1 FROM agent_sessions
                WHERE thread_id = %s AND user_id = %s
                LIMIT 1
                """,
                (thread_id, user_id),
            ).fetchone()
        return row is not None

    def append_user_message(self, thread_id: str, message: str, *, limit: int = 8) -> None:
        """追加用户消息，并删除超出 limit 的旧记录。"""
        text = (message or "").strip()
        if not text:
            return
        with self._pool.connection() as conn:
            conn.execute(
                """
                INSERT INTO agent_thread_user_messages (thread_id, content)
                VALUES (%s, %s)
                """,
                (thread_id, text),
            )
            conn.execute(
                """
                DELETE FROM agent_thread_user_messages
                WHERE thread_id = %s
                  AND id NOT IN (
                    SELECT id FROM agent_thread_user_messages
                    WHERE thread_id = %s
                    ORDER BY id DESC
                    LIMIT %s
                  )
                """,
                (thread_id, thread_id, limit),
            )

    def get_user_messages(self, thread_id: str, limit: int = 8) -> list[str]:
        """查询近期用户消息并按时间正序返回。"""
        with self._pool.connection() as conn:
            rows = conn.execute(
                """
                SELECT content FROM agent_thread_user_messages
                WHERE thread_id = %s
                ORDER BY id DESC
                LIMIT %s
                """,
                (thread_id, limit),
            ).fetchall()
        return [as_dict_row(row)["content"] for row in reversed(rows)]

    def delete_session(self, user_id: str, thread_id: str) -> bool:
        """删除会话与用户消息；成功后全清编排状态。"""
        with self._pool.connection() as conn:
            cursor = conn.execute(
                """
                DELETE FROM agent_sessions
                WHERE thread_id = %s AND user_id = %s
                """,
                (thread_id, user_id),
            )
            deleted = cursor.rowcount > 0
            # 仅归属校验通过后才清消息，避免跨用户误删。
            if deleted:
                conn.execute(
                    "DELETE FROM agent_thread_user_messages WHERE thread_id = %s",
                    (thread_id,),
                )
        if deleted:
            clear_thread_orchestration(thread_id)
        return deleted

    def set_thread_bpmn_snapshot(self, thread_id: str, snapshot: dict[str, Any]) -> None:
        """委托 BPMN 仓储保存快照。"""
        set_thread_bpmn_snapshot(thread_id, snapshot)

    def get_thread_bpmn_snapshot(self, thread_id: str) -> dict[str, Any] | None:
        """委托 BPMN 仓储读取快照。"""
        return get_thread_bpmn_snapshot(thread_id)

    def clear_thread_bpmn_snapshot(self, thread_id: str) -> None:
        """委托 BPMN 仓储清除快照。"""
        clear_thread_bpmn_snapshot(thread_id)


def _iso(value: Any) -> str:
    """将 datetime 转为 UTC ISO8601 字符串。"""
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    return str(value)
