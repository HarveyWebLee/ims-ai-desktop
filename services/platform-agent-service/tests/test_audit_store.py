"""审计存储筛选单测"""

from __future__ import annotations

from app.services.audit_store import InMemoryAuditStore, _filter_audit_entries


class TestAuditFilter:
    def test_filter_by_run_id(self):
        entries = [
            {"run_id": "run-a", "event_type": "tool_start"},
            {"run_id": "run-b", "event_type": "tool_end"},
        ]
        filtered = _filter_audit_entries(entries, run_id="run-a", event_type=None)
        assert len(filtered) == 1
        assert filtered[0]["run_id"] == "run-a"

    def test_filter_by_event_type(self):
        entries = [
            {"run_id": "run-a", "event_type": "tool_start"},
            {"run_id": "run-a", "event_type": "error"},
        ]
        filtered = _filter_audit_entries(entries, run_id=None, event_type="error")
        assert len(filtered) == 1
        assert filtered[0]["event_type"] == "error"

    def test_list_by_thread_with_filters(self):
        store = InMemoryAuditStore()
        store.append(
            thread_id="t1",
            user_id="u1",
            event_type="tool_start",
            run_id="run-1",
        )
        store.append(
            thread_id="t1",
            user_id="u1",
            event_type="error",
            run_id="run-2",
        )
        rows = store.list_by_thread("t1", event_type="error")
        assert len(rows) == 1
        assert rows[0]["event_type"] == "error"
