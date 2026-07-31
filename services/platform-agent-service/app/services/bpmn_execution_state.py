"""BPMN 图执行状态暂存（内存；HITL 走 checkpointer interrupt）。"""

from __future__ import annotations

from typing import Any

_bpmn_execution_states: dict[str, dict[str, Any]] = {}


def set_bpmn_execution_state(thread_id: str, payload: dict[str, Any]) -> None:
    """保存线程级 BPMN 执行状态。"""
    tid = (thread_id or "").strip()
    if not tid:
        return
    _bpmn_execution_states[tid] = dict(payload)


def get_bpmn_execution_state(thread_id: str) -> dict[str, Any] | None:
    """读取 BPMN 执行状态。"""
    tid = (thread_id or "").strip()
    if not tid:
        return None
    data = _bpmn_execution_states.get(tid)
    return dict(data) if data else None


def clear_bpmn_execution_state(thread_id: str) -> None:
    """清除 BPMN 执行状态。"""
    tid = (thread_id or "").strip()
    if not tid:
        return
    _bpmn_execution_states.pop(tid, None)
