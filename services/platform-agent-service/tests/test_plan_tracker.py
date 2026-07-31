"""PlanTracker 步骤状态与 plan_update payload 单测。"""

from __future__ import annotations

from app.graph.stream_envelope import PlanTracker


def test_on_tool_end_marks_awaiting_hitl_step_done():
    """HITL 暂停后工具完成，应能把 awaiting_hitl 步标为 done。"""
    tracker = PlanTracker(
        [
            {
                "id": "1",
                "label": "查询设备变量",
                "tool": "query_device_variables",
                "status": "awaiting_hitl",
            }
        ]
    )
    tracker._active_step_id = None

    payload = tracker.on_tool_end("query_device_variables", ok=True)

    assert payload == {
        "step_id": "1",
        "status": "done",
        "tool": "query_device_variables",
    }
    assert tracker.steps[0]["status"] == "done"


def test_on_tool_end_hard_failure_is_error_not_skipped():
    """硬失败（非用户取消）应标 error，不得标 skipped。"""
    tracker = PlanTracker(
        [
            {
                "id": "1",
                "label": "下发设备指令",
                "tool": "send_device_cmd",
                "status": "running",
            }
        ]
    )
    tracker._active_step_id = "1"

    payload = tracker.on_tool_end("send_device_cmd", ok=False, user_cancelled=False)

    assert payload == {
        "step_id": "1",
        "status": "error",
        "tool": "send_device_cmd",
    }
    assert tracker.steps[0]["status"] == "error"


def test_on_tool_end_user_cancelled_is_skipped():
    """用户主动取消才标 skipped。"""
    tracker = PlanTracker(
        [
            {
                "id": "1",
                "label": "下发设备指令",
                "tool": "send_device_cmd",
                "status": "running",
            }
        ]
    )
    tracker._active_step_id = "1"

    payload = tracker.on_tool_end("send_device_cmd", ok=False, user_cancelled=True)

    assert payload == {
        "step_id": "1",
        "status": "skipped",
        "tool": "send_device_cmd",
    }
    assert tracker.steps[0]["status"] == "skipped"


def test_on_tool_end_step_id_is_string_even_for_numeric_id():
    """plan_update 的 step_id 始终为字符串，避免前端 strict 比较失败。"""
    tracker = PlanTracker(
        [
            {
                "id": 2,
                "label": "查询设备变量",
                "tool": "query_device_variables",
                "status": "running",
            }
        ]
    )
    tracker._active_step_id = "2"

    payload = tracker.on_tool_end("query_device_variables", ok=True)

    assert payload is not None
    assert payload["step_id"] == "2"
    assert isinstance(payload["step_id"], str)


def test_on_interrupt_does_not_skip_completed_query_step_for_door_confirm():
    """send_device_cmd 确认 HITL 时，不得把仍在 running 的 get_device_detail 标 skipped/awaiting_hitl。"""
    tracker = PlanTracker(
        [
            {
                "id": "1",
                "label": "查看设备详情",
                "tool": "get_device_detail",
                "status": "running",
            }
        ]
    )
    tracker._active_step_id = "1"

    updates = tracker.on_interrupt("send_device_cmd")

    assert tracker.steps[0]["status"] == "running"
    assert not any(u.get("status") == "skipped" for u in updates)
    assert any(
        u.get("tool") == "send_device_cmd" and u.get("status") == "awaiting_hitl" for u in updates
    )
    assert len(tracker.steps) == 2
    assert tracker.steps[1]["tool"] == "send_device_cmd"


def test_on_interrupt_still_skips_stale_download_file_on_nav_hitl():
    """导航 HITL 时仍应跳过误触发的 export running 步。"""
    tracker = PlanTracker(
        [
            {
                "id": "1",
                "label": "导出",
                "tool": "download_file",
                "status": "running",
            }
        ]
    )
    tracker._active_step_id = "1"

    updates = tracker.on_interrupt("navigate_to")

    assert tracker.steps[0]["status"] == "skipped"
    assert {"step_id": "1", "status": "skipped", "tool": "download_file"} in updates
