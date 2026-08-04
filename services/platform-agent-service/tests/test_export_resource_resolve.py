"""导出 resource 会话上下文裁决单测。"""

from __future__ import annotations

from contracts.context import (
    current_recent_user_messages,
    current_user_utterance,
)
from contracts.export_infer import (
    EXPORT_RESOURCE_CONFIRMED_KEY,
    infer_download_resource,
    resolve_export_resource,
)
from contracts.tool_preflight import preflight_tool


class TestResolveExportResource:
    def test_explicit_sentry(self):
        d = resolve_export_resource("导出近三天岗哨交接")
        assert d.resource == "sentry_handover"
        assert d.need_choice is False

    def test_explicit_alarm_export(self):
        d = resolve_export_resource("导出告警")
        assert d.resource == "alarm_report"

    def test_unique_context_alarm(self):
        d = resolve_export_resource(
            "帮我导出一下",
            recent_messages=["今天未确认告警有多少？"],
        )
        assert d.resource == "alarm_report"
        assert d.reason == "unique_context"

    def test_ambiguous_multi_domain_context(self):
        d = resolve_export_resource(
            "导出",
            recent_messages=["查一下告警", "岗哨交接怎么看"],
        )
        assert d.need_choice is True
        assert "alarm_report" in d.candidates
        assert "sentry_handover" in d.candidates
        assert d.resource is None

    def test_no_context_lists_all(self):
        d = resolve_export_resource("导出")
        assert d.need_choice is True
        assert len(d.candidates) >= 4

    def test_infer_compat_defaults_alarm_when_ambiguous(self):
        assert infer_download_resource("导出") == "alarm_report"
        assert infer_download_resource("导出岗哨交接") == "sentry_handover"


class TestDownloadResourcePreflight:
    def test_no_session_keeps_explicit_resource(self):
        result = preflight_tool(
            "download_file",
            {"resource": "alarm_report", "start_time": "", "end_time": ""},
        )
        assert result.interrupt is not None
        assert result.interrupt["tool"] == "download_file"
        # 无会话上下文时不因歧义清空已给 resource，仍走时间 HITL
        assert "告警" in result.interrupt["message"] or "时间" in result.interrupt["message"]
        names = [f["name"] for f in result.interrupt["fields"]]
        assert "resource" not in names

    def test_ambiguous_utterance_asks_resource(self):
        utt = current_user_utterance.set("导出")
        recent = current_recent_user_messages.set(())
        try:
            result = preflight_tool(
                "download_file",
                {"resource": "sentry_handover", "start_time": "", "end_time": ""},
            )
            assert result.interrupt is not None
            assert "业务类型" in result.interrupt["message"]
            names = [f["name"] for f in result.interrupt["fields"]]
            assert "resource" in names
            assert "time_range" in names
            assert result.args.get("resource") == ""
        finally:
            current_user_utterance.reset(utt)
            current_recent_user_messages.reset(recent)

    def test_context_overrides_llm_guess(self):
        utt = current_user_utterance.set("导出")
        recent = current_recent_user_messages.set(("今天未确认告警有多少？",))
        try:
            result = preflight_tool(
                "download_file",
                {"resource": "sentry_handover", "start_time": "近三天", "end_time": ""},
            )
            assert result.interrupt is None
            assert result.args.get("resource") == "alarm_report"
        finally:
            current_user_utterance.reset(utt)
            current_recent_user_messages.reset(recent)

    def test_confirmed_resource_not_cleared(self):
        utt = current_user_utterance.set("导出")
        recent = current_recent_user_messages.set(())
        try:
            result = preflight_tool(
                "download_file",
                {
                    "resource": "duty_info",
                    EXPORT_RESOURCE_CONFIRMED_KEY: True,
                    "start_time": "",
                    "end_time": "",
                },
            )
            assert result.interrupt is not None
            assert "值班信息" in result.interrupt["message"]
            names = [f["name"] for f in result.interrupt["fields"]]
            assert "resource" not in names
        finally:
            current_user_utterance.reset(utt)
            current_recent_user_messages.reset(recent)
