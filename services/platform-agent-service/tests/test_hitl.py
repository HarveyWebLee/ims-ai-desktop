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
