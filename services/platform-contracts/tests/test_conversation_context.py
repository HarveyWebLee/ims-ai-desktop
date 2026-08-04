"""通用会话上下文与设备指称推断单测。"""

from __future__ import annotations

from contracts.context import (
    current_recent_user_messages,
    current_user_utterance,
)
from contracts.conversation_context import (
    TurnContext,
    enrich_tool_args_from_conversation,
    is_contextual_followup,
    merge_recent_user_messages,
)
from contracts.device_context import (
    extract_device_token_from_text,
    infer_device_token_from_conversation,
)


class TestDeviceContext:
    def test_control_and_paren_code(self):
        assert extract_device_token_from_text("给 502_DLJ 下发指令") == "502_DLJ"
        assert (
            extract_device_token_from_text("查看东大门（ANDUN_DEVICE_BH_001）详情")
            == "ANDUN_DEVICE_BH_001"
        )

    def test_pronoun_resolves_from_recent(self):
        token = infer_device_token_from_conversation(
            "给它下发指令",
            ["查询设备详情", "查一下 502多联机主机"],
        )
        assert token == "502多联机主机"

    def test_current_explicit_wins(self):
        token = infer_device_token_from_conversation(
            "给东大门开门",
            ["查一下 502多联机主机"],
        )
        assert token == "东大门"


class TestConversationContext:
    def test_followup_detection(self):
        assert is_contextual_followup("给它下发指令")
        assert is_contextual_followup("继续")
        assert is_contextual_followup("导出")
        assert not is_contextual_followup("查询近三天未确认告警")

    def test_merge_recent_excludes_current(self):
        merged = merge_recent_user_messages(
            frontend_recent=["查告警", "导出"],
            server_recent=["查告警", "导出", "给它下发指令"],
            current_message="给它下发指令",
            limit=5,
        )
        assert "给它下发指令" not in merged
        assert merged[-2:] == ["查告警", "导出"]

    def test_enrich_fills_device_and_time_when_empty(self):
        ut = current_user_utterance.set("给它下发指令")
        rt = current_recent_user_messages.set(("查近三天告警", "查一下502_DLJ"))
        try:
            device_args = enrich_tool_args_from_conversation(
                "send_device_cmd",
                {"action": "", "device_name": "", "device_code": ""},
            )
            assert device_args.get("device_code") == "502_DLJ" or device_args.get("device_name")

            time_args = enrich_tool_args_from_conversation(
                "query_alarms",
                {"start_time": "", "end_time": ""},
                turn=TurnContext(utterance="再查一遍", recent=("查近三天告警",)),
            )
            assert str(time_args.get("start_time") or "").strip()
        finally:
            current_user_utterance.reset(ut)
            current_recent_user_messages.reset(rt)

    def test_enrich_does_not_overwrite(self):
        args = enrich_tool_args_from_conversation(
            "send_device_cmd",
            {"device_name": "已指定设备"},
            turn=TurnContext(utterance="给它下发", recent=("查一下502_DLJ",)),
        )
        assert args["device_name"] == "已指定设备"
