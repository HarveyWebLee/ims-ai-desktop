"""
可观测仪表盘：跨会话 run 摘要与指标聚合（只读）。

数据源：agent_thread_traces + agent_audit_logs + agent_sessions。
读时聚合，不改 HITL / SSE 主链。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Literal, cast

from app.services.audit_store import audit_store
from app.services.session_store import session_store
from app.services.trace_store import trace_store

RunStatus = Literal["ok", "error", "interrupted"]


def resolve_time_window(
    *,
    hours: int | None = None,
    from_ms: int | None = None,
    to_ms: int | None = None,
) -> tuple[int, int]:
    """
    解析查询时间窗（毫秒 epoch）。

    默认最近 24h；hours 上限 720（30 天）。
    """
    now = datetime.now(UTC)
    end = to_ms if to_ms is not None else int(now.timestamp() * 1000)
    if from_ms is not None:
        start = from_ms
    else:
        h = hours if hours is not None else 24
        h = max(1, min(int(h), 720))
        start = int((now - timedelta(hours=h)).timestamp() * 1000)
    if start > end:
        start, end = end, start
    return start, end


def _event_kind(event: dict[str, Any]) -> str:
    return str(event.get("kind") or "")


def summarize_trace_run(
    run: dict[str, Any],
    *,
    thread_title: str | None = None,
) -> dict[str, Any]:
    """从单条 trace run 生成仪表盘摘要。"""
    raw_events = run.get("events")
    events: list[Any] = raw_events if isinstance(raw_events, list) else []
    has_error = any(_event_kind(e) == "error" for e in events if isinstance(e, dict))
    has_interrupt = any(_event_kind(e) == "interrupt" for e in events if isinstance(e, dict))

    tool_starts = sum(1 for e in events if isinstance(e, dict) and _event_kind(e) == "tool_start")
    tool_fail_count = 0
    for e in events:
        if not isinstance(e, dict) or _event_kind(e) != "tool_end":
            continue
        detail = e.get("detail") if isinstance(e.get("detail"), dict) else {}
        if isinstance(detail, dict) and detail.get("ok") is False:
            tool_fail_count += 1

    started_at = int(run.get("started_at") or 0)
    ended_at = int(run.get("ended_at") or 0)
    duration_ms = max(0, ended_at - started_at) if started_at and ended_at else None

    if has_error:
        status: RunStatus = "error"
    elif has_interrupt:
        # HITL 后父图常补发合成 done；不能用「无 done」判断中断
        status = "interrupted"
    else:
        status = "ok"

    user_preview = ""
    for e in events:
        if isinstance(e, dict) and _event_kind(e) == "user_message":
            detail = e.get("detail") if isinstance(e.get("detail"), dict) else {}
            if isinstance(detail, dict):
                user_preview = str(detail.get("message") or e.get("label") or "")
            else:
                user_preview = str(e.get("label") or "")
            break

    return {
        "thread_id": str(run.get("thread_id") or ""),
        "run_id": str(run.get("run_id") or ""),
        "thread_title": thread_title or "",
        "status": status,
        "duration_ms": duration_ms,
        "started_at": started_at,
        "ended_at": ended_at,
        "tool_call_count": tool_starts,
        "tool_fail_count": tool_fail_count,
        "has_interrupt": has_interrupt,
        "has_error": has_error,
        "has_full_trace": True,
        "user_message_preview": user_preview,
    }


def _percentile(sorted_values: list[int], pct: float) -> int | None:
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (len(sorted_values) - 1) * pct
    low = int(rank)
    high = min(low + 1, len(sorted_values) - 1)
    weight = rank - low
    return int(sorted_values[low] * (1 - weight) + sorted_values[high] * weight)


def _hour_bucket_ms(ts_ms: int) -> str:
    dt = datetime.fromtimestamp(ts_ms / 1000.0, tz=UTC)
    return dt.strftime("%Y-%m-%dT%H:00:00Z")


def _list_user_runs_via_sessions(
    user_id: str,
    *,
    start_ms: int,
    end_ms: int,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """经 session_store + trace_store 枚举用户 runs（内存与 PG 通用回退）。"""
    sessions = session_store.list_sessions(user_id)
    title_by_thread = {str(s.get("thread_id") or ""): str(s.get("title") or "") for s in sessions}
    collected: list[dict[str, Any]] = []
    for session in sessions:
        tid = str(session.get("thread_id") or "").strip()
        if not tid:
            continue
        # 每会话多取一些，再按时间窗过滤
        for run in trace_store.list_runs(tid, limit=50):
            started = int(run.get("started_at") or 0)
            if started and (started < start_ms or started > end_ms):
                continue
            if not started and end_ms:
                # 无时间戳时仍纳入（开发内存数据）
                pass
            collected.append(summarize_trace_run(run, thread_title=title_by_thread.get(tid, "")))
    collected.sort(key=lambda r: int(r.get("started_at") or 0), reverse=True)
    return collected[:limit]


def list_run_summaries(
    user_id: str,
    *,
    start_ms: int,
    end_ms: int,
    status: RunStatus | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    """列出当前用户跨会话 run 摘要；返回 (page, total)。"""
    list_fn = getattr(trace_store, "list_runs_for_user", None)
    if callable(list_fn):
        raw_runs = cast(
            list[dict[str, Any]],
            list_fn(
                user_id,
                start_ms=start_ms,
                end_ms=end_ms,
                limit=max(limit + offset, 500),
            ),
        )
        summaries = [summarize_trace_run(r, thread_title=r.get("thread_title")) for r in raw_runs]
    else:
        summaries = _list_user_runs_via_sessions(
            user_id, start_ms=start_ms, end_ms=end_ms, limit=max(limit + offset, 500)
        )

    if status:
        summaries = [s for s in summaries if s.get("status") == status]
    total = len(summaries)
    page = summaries[offset : offset + limit]
    return page, total


def _hitl_counts_for_user(
    user_id: str,
    *,
    start_ms: int,
    end_ms: int,
) -> dict[str, int]:
    """统计 hitl_lifecycle 各 action 次数。"""
    counts = {"emit": 0, "approve": 0, "reject": 0, "abort": 0}
    list_fn = getattr(audit_store, "list_hitl_lifecycle_for_user", None)
    if callable(list_fn):
        rows = cast(
            list[dict[str, Any]],
            list_fn(user_id, start_ms=start_ms, end_ms=end_ms),
        )
    else:
        rows = _hitl_via_sessions(user_id, start_ms=start_ms, end_ms=end_ms)

    for row in rows:
        raw_payload = row.get("payload_summary")
        payload: dict[str, Any] = raw_payload if isinstance(raw_payload, dict) else {}
        action = str(payload.get("action") or "").strip()
        if action in counts:
            counts[action] += 1
    return counts


def _hitl_via_sessions(
    user_id: str,
    *,
    start_ms: int,
    end_ms: int,
) -> list[dict[str, Any]]:
    """内存回退：按用户会话扫 audit。"""
    sessions = session_store.list_sessions(user_id)
    out: list[dict[str, Any]] = []
    for session in sessions:
        tid = str(session.get("thread_id") or "").strip()
        if not tid:
            continue
        for entry in audit_store.list_by_thread(tid, limit=200, event_type="hitl_lifecycle"):
            created = entry.get("created_at")
            if isinstance(created, str) and created:
                try:
                    created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    if created_dt.tzinfo is None:
                        created_dt = created_dt.replace(tzinfo=UTC)
                    created_ms = int(created_dt.timestamp() * 1000)
                    if created_ms < start_ms or created_ms > end_ms:
                        continue
                except ValueError:
                    pass
            out.append(entry)
    return out


def build_summary(
    user_id: str,
    *,
    start_ms: int,
    end_ms: int,
) -> dict[str, Any]:
    """聚合 summary 指标。"""
    runs, _total = list_run_summaries(
        user_id, start_ms=start_ms, end_ms=end_ms, limit=2000, offset=0
    )
    run_count = len(runs)
    error_count = sum(1 for r in runs if r.get("status") == "error")
    interrupted_count = sum(1 for r in runs if r.get("status") == "interrupted")
    ok_count = sum(1 for r in runs if r.get("status") == "ok")
    success_rate = (ok_count / run_count) if run_count else None

    durations = sorted(
        int(r["duration_ms"])
        for r in runs
        if isinstance(r.get("duration_ms"), int) and r["duration_ms"] is not None
    )
    tool_calls = sum(int(r.get("tool_call_count") or 0) for r in runs)
    tool_fails = sum(int(r.get("tool_fail_count") or 0) for r in runs)
    tool_fail_rate = (tool_fails / tool_calls) if tool_calls else None

    hitl = _hitl_counts_for_user(user_id, start_ms=start_ms, end_ms=end_ms)

    buckets: dict[str, dict[str, int]] = {}
    for r in runs:
        started = int(r.get("started_at") or 0)
        if not started:
            continue
        key = _hour_bucket_ms(started)
        bucket = buckets.setdefault(key, {"run_count": 0, "error_count": 0})
        bucket["run_count"] += 1
        if r.get("status") == "error":
            bucket["error_count"] += 1
    timeline = [
        {"bucket": k, "run_count": v["run_count"], "error_count": v["error_count"]}
        for k, v in sorted(buckets.items())
    ]

    return {
        "from_ms": start_ms,
        "to_ms": end_ms,
        "run_count": run_count,
        "ok_count": ok_count,
        "error_count": error_count,
        "interrupted_count": interrupted_count,
        "success_rate": success_rate,
        "latency_ms": {
            "p50": _percentile(durations, 0.50),
            "p95": _percentile(durations, 0.95),
        },
        "tool_calls": tool_calls,
        "tool_fail_count": tool_fails,
        "tool_fail_rate": tool_fail_rate,
        "hitl": hitl,
        "timeline": timeline,
    }


def get_run_detail(thread_id: str, run_id: str) -> dict[str, Any] | None:
    """下钻：enrich trace + 同 run audit。"""
    run = trace_store.get_run(thread_id, run_id)
    if not run:
        return None
    from app.services.trace_graph import enrich_trace_run

    enriched = enrich_trace_run(run)
    audits = audit_store.list_by_thread(thread_id, limit=200, run_id=run_id)
    summary = summarize_trace_run(run)
    return {
        "thread_id": thread_id,
        "run_id": run_id,
        "summary": summary,
        "run": enriched,
        "audit_logs": audits,
    }
