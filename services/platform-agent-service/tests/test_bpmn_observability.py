"""bpmn_observability 写入 audit 的单测。"""

from __future__ import annotations

from app.services.audit_store import InMemoryAuditStore, configure_audit_store
from app.services.bpmn_observability import (
    record_bpmn_compile,
    record_bpmn_execute,
    record_hitl_lifecycle,
)


def test_record_events_append_to_audit_store():
    store = InMemoryAuditStore()
    configure_audit_store(store)

    record_bpmn_compile(
        ok=True,
        fallback="none",
        reason="compiled",
        duration_ms=12,
        condition_count=1,
        thread_id="t-obs-1",
        user_id="u1",
    )
    record_bpmn_execute(
        node_id="cond_online",
        status="done",
        branch="if_online",
        thread_id="t-obs-1",
        user_id="u1",
    )
    record_hitl_lifecycle(
        action="emit",
        interrupt_type="confirm",
        tool="send_device_cmd",
        thread_id="t-obs-1",
        user_id="u1",
    )

    rows = store.list_by_thread("t-obs-1", limit=20)
    types = {r["event_type"] for r in rows}
    assert types == {"bpmn_compile", "bpmn_execute", "hitl_lifecycle"}
    compile_row = next(r for r in rows if r["event_type"] == "bpmn_compile")
    assert compile_row["payload_summary"]["ok"] is True
    assert compile_row["payload_summary"]["fallback"] == "none"
