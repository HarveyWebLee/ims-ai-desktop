"""
审计日志只读查询 API 模块

文件职责
--------
提供 `GET /api/agent/threads/{thread_id}/audit` 的处理逻辑，
按 thread_id 查询该会话下的审计事件（如 HITL 确认、工具调用摘要等），供运维与合规追溯。

在 Agent 流程中的位置
--------------------
位于对话 **事后查询** 链路：Agent 执行过程中 `audit_store.append()` 写入事件
（例如 resume.py 中用户 approve/reject 时）→ 本接口只读列出这些记录。

如何被调用
----------
- 路由：`app/main.py` 中 `@app.get("/api/agent/threads/{thread_id}/audit")`
- 前端：Trace / 会话详情等调试面板可拉取审计列表
- 权限：Postgres 模式下校验 thread 是否属于当前 user_id
"""

# ---------------------------------------------------------------------------
# 本项目：统一 JSON 响应
# ---------------------------------------------------------------------------
from app.api.response import fail, ok

# ---------------------------------------------------------------------------
# 本项目：会话读权限（与 get_thread_state 策略一致）
# ---------------------------------------------------------------------------
from app.api.thread_access import can_read_thread

# ---------------------------------------------------------------------------
# 本项目：从 Authorization 头解析当前用户 ID
# ---------------------------------------------------------------------------
from app.middleware.auth import get_current_user_id
from app.persistence.bootstrap import is_postgres_enabled

# ---------------------------------------------------------------------------
# 本项目：审计日志存储（内存或 Postgres 实现由 audit_store 封装）
# ---------------------------------------------------------------------------
from app.services.audit_store import audit_store


async def list_thread_audit(
    thread_id: str,
    *,
    limit: int = 100,
    run_id: str | None = None,
    event_type: str | None = None,
    authorization: str | None = None,
):
    """
    按 thread_id 分页查询审计日志。

    参数
    ----
    thread_id : str
        LangGraph 会话线程 ID，与 chat 请求中的 thread_id 一致。
    limit : int, 关键字-only 参数（调用时必须写 limit=）
        最多返回的日志条数，默认 100。
    authorization : str | None
        HTTP Authorization 头内容，用于识别 user_id。

    返回
    ----
    dict
        成功：ok({"thread_id": ..., "logs": [...]})
        失败：fail(...) 含业务错误码与说明

    异常
    ----
    本函数捕获 store 层异常由底层处理；鉴权失败返回 fail 而非 raise HTTPException。
    """
    # 空 thread_id 直接拒绝，避免全表扫描或误查
    if not thread_id:
        return fail(40001, "参数错误", "thread_id 不能为空")

    # await：auth 可能涉及异步 token 校验或远程调用
    user_id = await get_current_user_id(authorization)

    # Postgres：索引命中或 checkpoint/审计已有数据则允许；全新空会话返回空列表
    if is_postgres_enabled() and not can_read_thread(user_id, thread_id):
        return ok({"thread_id": thread_id, "logs": []})

    # 从 audit_store 按 thread 倒序取最近 limit 条
    logs = audit_store.list_by_thread(
        thread_id,
        limit=limit,
        run_id=(run_id or "").strip() or None,
        event_type=(event_type or "").strip() or None,
    )
    return ok({"thread_id": thread_id, "logs": logs})
