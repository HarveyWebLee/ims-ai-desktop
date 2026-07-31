"""
会话读权限校验模块

文件职责
--------
判断「当前用户能否读取某 thread 的附属数据」
（审计列表、Trace、会话 state、BPMN 快照等）。

白话概念
--------
对话用 thread_id 标识。Postgres 模式下会话按 user_id 隔离，
不能让 A 用户随便打开 B 用户的 thread。
本函数回答：这个人能不能读这个会话？

在 Agent 流程中的位置
--------------------
  audit / trace / sessions.get_thread_state / bpmn 读接口
    → can_read_thread(user_id, thread_id)
    → True 才继续查库；False 则 404 或空列表（见各 API）

权限策略
--------
1. 非 Postgres（内存模式）→ 一律允许（本地开发无多租户）
2. Postgres：仅当 agent_sessions 命中 user_id + thread_id → 允许
3. 不再回退 checkpoint/audit：避免跨用户读取，并保证删会话后无法经残留状态恢复

如何被调用
----------
- `app/api/audit.py`、`trace.py`、`bpmn.py`、`sessions.py` 等在读附属数据前调用
- 依赖：session_store、is_postgres_enabled
"""

from __future__ import annotations

from app.persistence.bootstrap import is_postgres_enabled
from app.services.session_store import session_store


def can_read_thread(user_id: str, thread_id: str) -> bool:
    """
    判断当前用户是否可读指定 thread 的附属数据。

    参数
    ----
    user_id : str
        由 Authorization 解析出的用户标识（如 ``user_a1b2c3d4`` 或 ``anonymous``）。
    thread_id : str
        对话线程 ID。

    返回
    ----
    bool
        True 允许读取；False 应拒绝（调用方返回 404 或空列表）。

    说明
    ----
    非 Postgres 模式不做隔离，一律 ``True``。
    """
    if not is_postgres_enabled():
        return True

    return session_store.has_thread(user_id, thread_id)
