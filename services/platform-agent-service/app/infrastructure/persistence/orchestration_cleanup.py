"""线程编排状态清理：BPMN 快照 + 条件图 execution_state。"""

from __future__ import annotations

from app.infrastructure.persistence.bpmn_repository import clear_thread_bpmn_snapshot


def clear_thread_orchestration(thread_id: str) -> None:
    """清除本线程编排暂存（BPMN 快照与 bpmn_execution_state）。"""
    from contracts.agent_debug import agent_debug, orchestration_snapshot

    before = orchestration_snapshot(thread_id)
    clear_thread_bpmn_snapshot(thread_id)
    from app.services.bpmn_execution_state import clear_bpmn_execution_state

    clear_bpmn_execution_state(thread_id)
    after = orchestration_snapshot(thread_id)
    agent_debug(
        "store.clear_thread_orchestration",
        thread_id=thread_id,
        before=before,
        after=after,
    )
