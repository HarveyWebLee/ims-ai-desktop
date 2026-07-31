"""
会话列表与线程状态查询 API 模块

文件职责
--------
1. `GET /api/agent/sessions` — 列出当前用户的会话摘要（标题、thread_id、更新时间等）
2. `GET /api/agent/threads/{thread_id}/state` — 读取指定 thread 的历史消息（LangGraph checkpoint）

在 Agent 流程中的位置
--------------------
- **sessions**：侧栏「历史会话」列表的数据源；chat 时会 upsert 会话元数据
- **state**：用户切换会话或刷新页面时恢复对话气泡；与 chat SSE 中的 checkpoint 互补

如何被调用
----------
- 路由：见 `app/main.py` 的 `/api/agent/sessions` 与 `/api/agent/threads/{thread_id}/state`
- chat.py 在每次对话前调用 `session_store.upsert_session` 更新索引
- get_thread_state 内部调用 `get_thread_ui_messages` 从 LangGraph checkpointer 读消息
"""

# ---------------------------------------------------------------------------
# 本项目：统一 JSON 响应
# ---------------------------------------------------------------------------
from app.api.response import fail, ok

# ---------------------------------------------------------------------------
# 本项目：会话元数据存储（user_id ↔ thread_id 映射）
# ---------------------------------------------------------------------------
from app.api.thread_access import can_read_thread

# ---------------------------------------------------------------------------
# 本项目：用户身份解析
# ---------------------------------------------------------------------------
from app.middleware.auth import get_current_user_id
from app.services.session_store import session_store

# ---------------------------------------------------------------------------
# 本项目：从 LangGraph checkpoint 读取 thread 消息列表
# ---------------------------------------------------------------------------
from app.services.thread_history import get_thread_ui_messages


async def list_sessions(authorization: str | None = None):
    """
    返回当前登录用户的所有 Agent 会话摘要。

    参数
    ----
    authorization : str | None
        Bearer token 等，由 FastAPI 从 Header 传入。

    返回
    ----
    dict
        ok({"sessions": [...]})，sessions 元素结构由 session_store 定义
        （通常含 thread_id、title、updated_at 等）。

    异常
    ----
    鉴权失败时 get_current_user_id 的行为由 middleware 决定。
    """
    user_id = await get_current_user_id(authorization)
    sessions = session_store.list_sessions(user_id)
    return ok({"sessions": sessions})


async def get_thread_state(thread_id: str, authorization: str | None = None):
    """
    获取指定 thread 的消息历史（用于前端恢复对话 UI）。

    参数
    ----
    thread_id : str
        会话线程 ID。
    authorization : str | None
        鉴权头。

    返回
    ----
    dict
        成功：ok({"thread_id": ..., "messages": [...]})
        失败：thread 不存在且无权访问时 fail(40404, ...)

    业务说明
    --------
    Postgres 模式下若 session 索引尚未写入但 checkpoint 已有消息（索引延迟），
    仍允许加载消息，避免用户刚发完第一条消息就切页导致空白。
    """
    if not thread_id:
        return fail(40001, "参数错误", "thread_id 不能为空")

    user_id = await get_current_user_id(authorization)

    from app.persistence.bootstrap import is_postgres_enabled

    if is_postgres_enabled() and not can_read_thread(user_id, thread_id):
        return fail(40404, "会话不存在", "无权访问该会话或会话已过期")

    # AsyncPostgresSaver 须 await aget；内存 InMemorySaver 的 aget 亦可
    messages = await get_thread_ui_messages(thread_id)
    from app.services.session_store import get_thread_bpmn_snapshot

    bpmn_snapshot = get_thread_bpmn_snapshot(thread_id)
    return ok(
        {
            "thread_id": thread_id,
            "messages": messages,
            "bpmn_snapshot": bpmn_snapshot,
        }
    )


async def delete_session(thread_id: str, authorization: str | None = None):
    """删除当前用户的一条会话索引，并清理 Checkpoint / Trace / Audit。"""
    if not thread_id:
        return fail(40001, "参数错误", "thread_id 不能为空")

    user_id = await get_current_user_id(authorization)
    deleted = session_store.delete_session(user_id, thread_id)
    if not deleted:
        return fail(40404, "会话不存在", "无权删除该会话或会话已不存在")

    from app.services.thread_cleanup import delete_thread_persistence

    try:
        await delete_thread_persistence(thread_id)
    except Exception:
        return fail(50001, "删除失败", "会话索引已删除，但持久化数据清理失败，请稍后重试")

    return ok({"thread_id": thread_id, "deleted": True})
