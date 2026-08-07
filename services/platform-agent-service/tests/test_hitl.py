"""HITL：MCP McpHitlSignal + Agent interrupt_or_raise。"""

from __future__ import annotations

import pytest

from contracts.hitl import (
    McpHitlSignal,
    ask_user_confirm,
    ask_user_params,
    is_hitl_approve,
    is_hitl_reject,
    merge_hitl_resume_args,
)


class TestAskUserParams:
    def test_complete_args_passthrough(self):
        current = {"start_time": "2026-01-01", "end_time": "2026-01-02"}
        fields = [
            {"name": "start_time", "required": True, "type": "string"},
            {"name": "end_time", "required": True, "type": "string"},
        ]
        assert (
            ask_user_params(
                tool="query_alarms",
                message="补参",
                fields=fields,
                current=current,
            )
            == current
        )

    def test_missing_raises_mcp_hitl_signal(self):
        with pytest.raises(McpHitlSignal) as exc_info:
            ask_user_params(
                tool="query_alarms",
                message="请补充时间",
                fields=[{"name": "start_time", "required": True, "type": "string"}],
                current={},
            )
        assert exc_info.value.payload["type"] == "ask_params"
        assert exc_info.value.payload["tool"] == "query_alarms"

    def test_empty_filter_fields_omitted_from_current(self):
        """LLM/工具默认空串不得进入 interrupt.current，避免多选空白已选项。"""
        with pytest.raises(McpHitlSignal) as exc_info:
            ask_user_params(
                tool="query_alarms",
                message="请补充时间",
                fields=[
                    {"name": "time_range", "required": True, "type": "datetime_range"},
                    {
                        "name": "status",
                        "required": False,
                        "type": "select",
                        "mode": "multiple",
                    },
                    {
                        "name": "alarm_category_id",
                        "required": False,
                        "type": "async_select",
                        "mode": "multiple",
                    },
                    {
                        "name": "alarm_rank_id",
                        "required": False,
                        "type": "async_select",
                        "mode": "multiple",
                    },
                    {"name": "device_name", "required": False, "type": "text"},
                ],
                current={
                    "start_time": "",
                    "end_time": "",
                    "device_name": "岗亭-1",
                    "status": "",
                    "alarm_category_id": [""],
                    "alarm_rank_id": "",
                },
            )
        current = exc_info.value.payload.get("current") or {}
        assert current == {"device_name": "岗亭-1"}


class TestAskUserConfirm:
    def test_raises_without_bypass(self):
        from contracts.context import current_hitl_confirm_bypass

        token = current_hitl_confirm_bypass.set(False)
        try:
            with pytest.raises(McpHitlSignal) as exc_info:
                ask_user_confirm(tool="download_file", message="确认导出？")
            assert exc_info.value.payload["type"] == "confirm"
        finally:
            current_hitl_confirm_bypass.reset(token)

    def test_bypass_returns_true(self):
        from contracts.context import current_hitl_confirm_bypass

        token = current_hitl_confirm_bypass.set(True)
        try:
            assert ask_user_confirm(tool="download_file", message="确认导出？") is True
        finally:
            current_hitl_confirm_bypass.reset(token)


class TestResumeHelpers:
    def test_merge_and_reject_approve(self):
        merged = merge_hitl_resume_args(
            {"type": "respond", "args": {"device_code": "D1"}},
            {"name": "x"},
        )
        assert merged["device_code"] == "D1"
        assert is_hitl_reject({"type": "reject"})
        assert is_hitl_approve({"type": "approve"})
