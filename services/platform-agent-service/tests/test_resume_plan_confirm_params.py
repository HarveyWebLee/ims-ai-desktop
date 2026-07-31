"""plan_confirm 批准后参数合并（与 parent_graph.plan_confirm_node 对齐）。"""

from __future__ import annotations

from typing import Any

from app.services.plan_confirm import merge_plan_params, propagate_query_alarm_filter_params


def _merge_like_parent_graph(
    user_message: str,
    steps: list[dict[str, Any]],
    existing_params: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """复现父图批准后的参数合并：推断值打底，已有 params 覆盖。"""
    active_tools = {str(s.get("tool") or "") for s in steps if s.get("tool")}
    inferred = merge_plan_params(user_message, steps)
    merged: dict[str, dict[str, Any]] = {}
    for tool in active_tools:
        base = {**dict(inferred.get(tool) or {}), **dict(existing_params.get(tool) or {})}
        if base:
            merged[tool] = base
    propagate_query_alarm_filter_params(merged, steps)
    return merged


def test_merge_plan_params_for_new_download_step():
    steps = [
        {"id": "1", "label": "查询告警", "tool": "query_alarms", "status": "pending"},
        {"id": "2", "label": "导出报表", "tool": "download_file", "status": "pending"},
    ]
    existing = {
        "query_alarms": {"start_time": "近三天", "end_time": "现在"},
    }

    merged = _merge_like_parent_graph(
        "查近三天未处理告警然后导出",
        steps,
        existing,
    )

    assert merged["query_alarms"]["start_time"] == "近三天"
    assert merged["download_file"]["resource"] == "alarm_report"
    assert str(merged["download_file"].get("status") or "").strip()


def test_merge_plan_params_drops_removed_tool():
    steps = [
        {"id": "1", "label": "查询告警", "tool": "query_alarms", "status": "pending"},
    ]
    existing = {
        "query_alarms": {"start_time": "近三天", "end_time": "现在"},
        "download_file": {"resource": "alarm_report"},
    }

    merged = _merge_like_parent_graph("查近三天告警", steps, existing)

    assert "query_alarms" in merged
    assert "download_file" not in merged


def test_merge_plan_params_existing_overrides_inferred():
    steps = [
        {"id": "1", "label": "查询告警", "tool": "query_alarms", "status": "pending"},
    ]
    existing = {
        "query_alarms": {"start_time": "近一周", "end_time": "现在", "status": "PROCESSED"},
    }

    merged = _merge_like_parent_graph("查近三天未处理告警", steps, existing)

    assert merged["query_alarms"]["start_time"] == "近一周"
    assert merged["query_alarms"]["status"] == "PROCESSED"
