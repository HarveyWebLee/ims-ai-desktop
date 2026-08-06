"""通用会话上下文与设备指称推断单测。"""

from __future__ import annotations

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
    """device_context 纯文本抽取仍可供 Prompt/辅助分析，但不再写入 tool args。"""

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

    def test_alarm_time_query_is_not_device_name(self):
        assert extract_device_token_from_text("查询近一月的报警数据") is None
        assert extract_device_token_from_text("查询近三天未确认告警") is None
        assert (
            infer_device_token_from_conversation(
                "执行上面未完成的任务",
                ["查询近一月的报警数据"],
            )
            is None
        )

    def test_device_of_alarm_still_extracts_name(self):
        assert extract_device_token_from_text("查一下一号泵的报警") == "一号泵"
        assert extract_device_token_from_text("查询东大门告警") == "东大门"


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

    def test_enrich_is_passthrough_no_regex_fill(self):
        """enrich 分路已关闭：不从会话正则补 device/time。"""
        args = enrich_tool_args_from_conversation(
            "send_device_cmd",
            {"action": "", "device_name": "", "device_code": ""},
            turn=TurnContext(utterance="给它下发指令", recent=("查一下502_DLJ",)),
        )
        assert args == {"action": "", "device_name": "", "device_code": ""}

        time_args = enrich_tool_args_from_conversation(
            "query_alarms",
            {"start_time": "", "end_time": ""},
            turn=TurnContext(utterance="再查一遍", recent=("查近三天告警",)),
        )
        assert time_args == {"start_time": "", "end_time": ""}

    def test_enrich_preserves_explicit_args(self):
        args = enrich_tool_args_from_conversation(
            "query_alarms",
            {"start_time": "近一月", "end_time": ""},
            turn=TurnContext(
                utterance="执行上面未完成的任务",
                recent=("查询近一月的报警数据",),
            ),
        )
        assert args == {"start_time": "近一月", "end_time": ""}
