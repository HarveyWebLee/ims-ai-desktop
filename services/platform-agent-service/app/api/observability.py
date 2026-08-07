"""
可观测仪表盘只读 API。

提供跨会话 summary / runs 列表 / run 下钻，供桌面设置页展示。
不改写 HITL / SSE 主链。
"""

from __future__ import annotations

from typing import cast

from app.api.response import fail, ok
from app.api.thread_access import can_read_thread
from app.middleware.auth import get_current_user_id
from app.persistence.bootstrap import is_postgres_enabled
from app.services.observability_query import (
    RunStatus,
    build_summary,
    get_run_detail,
    list_run_summaries,
    resolve_time_window,
)


async def get_observability_summary(
    *,
    hours: int | None = None,
    from_ms: int | None = None,
    to_ms: int | None = None,
    authorization: str | None = None,
):
    """聚合当前用户时间窗内的运行指标。"""
    user_id = await get_current_user_id(authorization)
    start_ms, end_ms = resolve_time_window(hours=hours, from_ms=from_ms, to_ms=to_ms)
    data = build_summary(user_id, start_ms=start_ms, end_ms=end_ms)
    return ok(data)


async def list_observability_runs(
    *,
    hours: int | None = None,
    from_ms: int | None = None,
    to_ms: int | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    authorization: str | None = None,
):
    """跨会话列出当前用户的 run 摘要。"""
    user_id = await get_current_user_id(authorization)
    start_ms, end_ms = resolve_time_window(hours=hours, from_ms=from_ms, to_ms=to_ms)

    status_filter: RunStatus | None = None
    normalized = (status or "").strip()
    if normalized in ("ok", "error", "interrupted"):
        status_filter = cast(RunStatus, normalized)

    limit = max(1, min(int(limit), 200))
    offset = max(0, int(offset))

    runs, total = list_run_summaries(
        user_id,
        start_ms=start_ms,
        end_ms=end_ms,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return ok(
        {
            "from_ms": start_ms,
            "to_ms": end_ms,
            "total": total,
            "limit": limit,
            "offset": offset,
            "runs": runs,
        }
    )


async def get_observability_run_detail(
    thread_id: str,
    run_id: str,
    *,
    authorization: str | None = None,
):
    """单 run 下钻：trace + audit。"""
    tid = (thread_id or "").strip()
    rid = (run_id or "").strip()
    if not tid or not rid:
        return fail(40001, "参数错误", "thread_id / run_id 不能为空")

    user_id = await get_current_user_id(authorization)
    if is_postgres_enabled() and not can_read_thread(user_id, tid):
        return fail(40404, "会话不存在", "无权访问该会话")

    detail = get_run_detail(tid, rid)
    if not detail:
        return fail(40404, "Trace 不存在", f"run_id={rid}")
    return ok(detail)
