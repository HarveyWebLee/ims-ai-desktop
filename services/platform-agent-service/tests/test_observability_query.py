"""可观测聚合查询单测（内存 store）。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.services.audit_store import InMemoryAuditStore, configure_audit_store
from app.services.observability_query import (
    build_summary,
    list_run_summaries,
    resolve_time_window,
    summarize_trace_run,
)
from app.services.session_store import InMemorySessionStore, configure_session_store
from app.services.trace_store import InMemoryTraceStore, configure_trace_store


def _ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


class TestObservabilityQuery:
    def setup_method(self) -> None:
        self.sessions = InMemorySessionStore()
        self.traces = InMemoryTraceStore()
        self.audits = InMemoryAuditStore()
        configure_session_store(self.sessions)
        configure_trace_store(self.traces)
        configure_audit_store(self.audits)

        self.user = "user_obs"
        self.sessions.upsert_session(self.user, "thread-a", title="会话 A")
        now = datetime.now(UTC)
        started = _ms(now - timedelta(minutes=5))
        ended = _ms(now - timedelta(minutes=4))
        self.traces.save_run(
            {
                "thread_id": "thread-a",
                "run_id": "run-ok",
                "started_at": started,
                "ended_at": ended,
                "events": [
                    {
                        "id": "1",
                        "ts": started,
                        "kind": "user_message",
                        "label": "用户输入",
                        "detail": {"message": "查告警"},
                    },
                    {
                        "id": "2",
                        "ts": started + 10,
                        "kind": "tool_start",
                        "label": "工具开始",
                        "detail": {"tool": "query_alarms"},
                    },
                    {
                        "id": "3",
                        "ts": started + 20,
                        "kind": "tool_end",
                        "label": "工具完成",
                        "detail": {"tool": "query_alarms", "ok": True},
                    },
                    {
                        "id": "4",
                        "ts": ended,
                        "kind": "done",
                        "label": "结束",
                        "detail": {},
                    },
                ],
            }
        )
        err_started = _ms(now - timedelta(minutes=2))
        err_ended = _ms(now - timedelta(minutes=1))
        self.traces.save_run(
            {
                "thread_id": "thread-a",
                "run_id": "run-err",
                "started_at": err_started,
                "ended_at": err_ended,
                "events": [
                    {
                        "id": "e1",
                        "ts": err_started,
                        "kind": "user_message",
                        "label": "用户输入",
                        "detail": {"message": "失败用例"},
                    },
                    {
                        "id": "e2",
                        "ts": err_ended,
                        "kind": "error",
                        "label": "执行错误",
                        "detail": {"message": "boom"},
                    },
                ],
            }
        )
        self.audits.append(
            thread_id="thread-a",
            user_id=self.user,
            event_type="hitl_lifecycle",
            run_id="run-ok",
            payload_summary={"action": "approve", "interrupt_type": "confirm"},
        )

    def test_resolve_time_window_default(self):
        start, end = resolve_time_window()
        assert end >= start
        assert end - start >= 23 * 3600 * 1000

    def test_summarize_status(self):
        runs = self.traces.list_runs("thread-a", limit=10)
        by_id = {r["run_id"]: summarize_trace_run(r) for r in runs}
        assert by_id["run-ok"]["status"] == "ok"
        assert by_id["run-err"]["status"] == "error"
        assert by_id["run-ok"]["tool_call_count"] == 1

    def test_summarize_interrupt_with_synthetic_done(self):
        """HITL 后父图常补合成 done；有 interrupt 应标 interrupted 而非 ok。"""
        run = {
            "thread_id": "thread-hitl",
            "run_id": "run-hitl",
            "started_at": 1,
            "ended_at": 100,
            "events": [
                {"id": "1", "ts": 1, "kind": "user_message", "label": "输入", "detail": {}},
                {
                    "id": "2",
                    "ts": 50,
                    "kind": "interrupt",
                    "label": "待确认",
                    "detail": {"type": "confirm"},
                },
                {"id": "3", "ts": 100, "kind": "done", "label": "结束", "detail": {}},
            ],
        }
        summary = summarize_trace_run(run)
        assert summary["status"] == "interrupted"

    def test_list_and_summary(self):
        start, end = resolve_time_window(hours=24)
        page, total = list_run_summaries(self.user, start_ms=start, end_ms=end, limit=10, offset=0)
        assert total == 2
        assert len(page) == 2
        summary = build_summary(self.user, start_ms=start, end_ms=end)
        assert summary["run_count"] == 2
        assert summary["error_count"] == 1
        assert summary["ok_count"] == 1
        assert summary["hitl"]["approve"] == 1
        assert summary["latency_ms"]["p50"] is not None

    def test_status_filter(self):
        start, end = resolve_time_window(hours=24)
        page, total = list_run_summaries(
            self.user,
            start_ms=start,
            end_ms=end,
            status="error",
            limit=10,
            offset=0,
        )
        assert total == 1
        assert page[0]["run_id"] == "run-err"
