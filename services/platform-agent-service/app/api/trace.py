"""
执行 Trace 只读查询 API 模块（Phase 3）

文件职责
--------
提供 `GET /api/agent/threads/{thread_id}/trace` 的处理逻辑，
查询 LangGraph Agent 单次 run 的步骤级 Trace（Plan、工具调用、重试等），供调试面板展示。

在 Agent 流程中的位置
--------------------
- **写入**：graph/builder 执行 stream_chat / stream_resume 时由 trace_store 记录各 step
- **读取**：本模块只读；与 audit 分离（audit 侧重合规事件，trace 侧重执行拓扑）

如何被调用
----------
- 路由：`app/main.py` → `get_thread_trace(thread_id, run_id?, authorization?)`
- 可选 query `run_id`：指定则返回单条 run 详情；省略则返回最近 20 条 run 摘要列表
"""

# ---------------------------------------------------------------------------
# 本项目：统一 JSON 响应
# ---------------------------------------------------------------------------
from app.api.response import fail, ok

# ---------------------------------------------------------------------------
# 本项目：会话读权限
# ---------------------------------------------------------------------------
from app.api.thread_access import can_read_thread

# ---------------------------------------------------------------------------
# 本项目：用户身份
# ---------------------------------------------------------------------------
from app.middleware.auth import get_current_user_id
from app.persistence.bootstrap import is_postgres_enabled

# ---------------------------------------------------------------------------
# 本项目：Trace 存储（run 级别步骤树）
# ---------------------------------------------------------------------------
from app.services.trace_store import trace_store


async def get_thread_trace(
    thread_id: str,
    *,
    run_id: str | None = None,
    authorization: str | None = None,
):
    """
    查询指定 thread 的 Trace 数据。

    参数
    ----
    thread_id : str
        会话线程 ID。
    run_id : str | None, 关键字-only
        若提供，只返回该次 Agent run 的完整 trace；否则返回 run 列表。
    authorization : str | None
        鉴权头。

    返回
    ----
    dict
        - 带 run_id：ok({"thread_id", "run": {...}}) 或 fail(40404) 若 run 不存在
        - 无 run_id：ok({"thread_id", "runs": [...]})，最多 20 条

    异常
    ----
    不向外抛未处理异常；权限与会话校验失败返回 fail 字典。
    """
    if not thread_id:
        return fail(40001, "参数错误", "thread_id 不能为空")

    user_id = await get_current_user_id(authorization)

    if is_postgres_enabled() and not can_read_thread(user_id, thread_id):
        return fail(40404, "会话不存在", "无权访问该会话")

    # 分支：单 run 详情 vs 列表
    if run_id:
        run = trace_store.get_run(thread_id, run_id)
        if not run:
            return fail(40404, "Trace 不存在", f"run_id={run_id}")
        from app.services.trace_graph import enrich_trace_run

        return ok({"thread_id": thread_id, "run": enrich_trace_run(run)})

    runs = trace_store.list_runs(thread_id, limit=20)
    from app.services.trace_graph import enrich_trace_run

    return ok(
        {
            "thread_id": thread_id,
            "runs": [enrich_trace_run(r) for r in runs],
        }
    )
