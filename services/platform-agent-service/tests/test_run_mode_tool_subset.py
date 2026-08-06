"""会话运行模式与工具子集（P0-1 / P0-2）。"""

from __future__ import annotations

import pytest

from contracts.context import current_run_mode, normalize_run_mode
from contracts.hitl import McpHitlSignal, ask_user_confirm
from contracts.tool_catalog_loader import is_write_tool


class TestNormalizeRunMode:
    def test_defaults_and_valid(self):
        assert normalize_run_mode(None) == "confirm"
        assert normalize_run_mode("") == "confirm"
        assert normalize_run_mode("bogus") == "confirm"
        assert normalize_run_mode("readonly") == "readonly"
        assert normalize_run_mode("AUTONOMOUS") == "autonomous"


class TestAskUserConfirmRunMode:
    def test_autonomous_skips_confirm(self):
        bypass = current_run_mode.set("autonomous")
        try:
            assert ask_user_confirm(tool="batch_confirm_alarms", message="确认？") is True
        finally:
            current_run_mode.reset(bypass)

    def test_confirm_still_raises(self):
        mode = current_run_mode.set("confirm")
        from contracts.context import current_hitl_confirm_bypass

        bypass = current_hitl_confirm_bypass.set(False)
        try:
            with pytest.raises(McpHitlSignal) as exc_info:
                ask_user_confirm(tool="batch_confirm_alarms", message="确认？")
            assert exc_info.value.payload["type"] == "confirm"
        finally:
            current_hitl_confirm_bypass.reset(bypass)
            current_run_mode.reset(mode)


class TestWriteToolDetection:
    def test_known_write_and_read(self):
        assert is_write_tool("batch_confirm_alarms") is True
        assert is_write_tool("send_device_cmd") is True
        assert is_write_tool("download_file") is True
        assert is_write_tool("query_alarms") is False
        assert is_write_tool("navigate_to") is False


class TestToolSubset:
    def test_readonly_excludes_write(self):
        from app.services.tool_subset import select_tool_subset

        available = frozenset(
            {
                "query_alarms",
                "batch_confirm_alarms",
                "navigate_to",
                "retrieve_knowledge",
                "send_device_cmd",
            }
        )
        result = select_tool_subset(
            run_mode="readonly",
            message="批量确认告警",
            available_names=available,
        )
        assert "batch_confirm_alarms" not in result.tool_names
        assert "send_device_cmd" not in result.tool_names
        assert "query_alarms" in result.tool_names
        assert "retrieve_knowledge" in result.tool_names

    def test_alarm_domain_filters(self):
        from app.services.tool_subset import select_tool_subset

        available = frozenset(
            {
                "query_alarms",
                "batch_confirm_alarms",
                "query_devices",
                "send_device_cmd",
                "navigate_to",
                "retrieve_knowledge",
            }
        )
        result = select_tool_subset(
            run_mode="confirm",
            message="查询近三天未处理告警",
            available_names=available,
        )
        assert result.fallback_full is False
        assert result.strategy == "domain"
        assert "alarm" in result.domains
        assert "query_alarms" in result.tool_names
        assert "batch_confirm_alarms" in result.tool_names
        assert "retrieve_knowledge" in result.tool_names
        assert "navigate_to" in result.tool_names
        assert "send_device_cmd" not in result.tool_names

    def test_safe_default_when_no_domain(self):
        """无领域命中时用 safe_default（非写），不再回退全量。"""
        from app.services.tool_subset import select_tool_subset

        available = frozenset(
            {
                "query_alarms",
                "query_devices",
                "batch_confirm_alarms",
                "send_device_cmd",
                "retrieve_knowledge",
            }
        )
        result = select_tool_subset(
            run_mode="confirm",
            message="你好",
            available_names=available,
        )
        assert result.fallback_full is False
        assert result.strategy == "safe_default"
        assert "query_alarms" in result.tool_names
        assert "query_devices" in result.tool_names
        assert "retrieve_knowledge" in result.tool_names
        assert "batch_confirm_alarms" not in result.tool_names
        assert "send_device_cmd" not in result.tool_names

    def test_domain_keyword_without_matched_tools_uses_safe_default(self):
        from app.services.tool_subset import select_tool_subset

        # 命中 alarm 关键词，但 available 中无 alarm 工具
        available = frozenset({"query_devices", "send_device_cmd", "retrieve_knowledge"})
        result = select_tool_subset(
            run_mode="confirm",
            message="查一下告警",
            available_names=available,
        )
        assert result.strategy == "safe_default"
        assert "alarm" in result.domains
        assert "send_device_cmd" not in result.tool_names
        assert "query_devices" in result.tool_names

    def test_multi_domain_union_condition_sentence(self):
        """条件句多域并集：告警查询 ∪ 开门写工具同时可绑。"""
        from app.services.tool_subset import select_tool_subset

        available = frozenset(
            {
                "query_alarms",
                "batch_confirm_alarms",
                "query_devices",
                "send_device_cmd",
                "navigate_to",
                "retrieve_knowledge",
            }
        )
        result = select_tool_subset(
            run_mode="confirm",
            message="若最近三天有告警则开门",
            available_names=available,
        )
        assert result.strategy == "domain"
        assert "alarm" in result.domains
        assert "device" in result.domains
        assert "query_alarms" in result.tool_names
        assert "send_device_cmd" in result.tool_names

    def test_condition_colloquial_open_augments_device(self):
        """口语「开了」在条件句下仍并入 device（防漏）。"""
        from app.services.tool_subset import infer_domains_from_text

        domains = infer_domains_from_text("有告警就把东门开了")
        assert "alarm" in domains
        assert "device" in domains

    def test_remember_thread_subset(self):
        from app.services.tool_subset import (
            clear_thread_tool_subset,
            get_remembered_thread_tool_subset,
            remember_thread_tool_subset,
        )

        tid = "thread-test-subset"
        names = frozenset({"query_alarms", "retrieve_knowledge"})
        remember_thread_tool_subset(tid, names)
        assert get_remembered_thread_tool_subset(tid) == names
        clear_thread_tool_subset(tid)
        assert get_remembered_thread_tool_subset(tid) is None
