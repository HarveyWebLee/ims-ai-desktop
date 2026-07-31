"""Phase C1 纯对话意图识别单测"""

from __future__ import annotations

from app.services.chat_intent import is_chat_only_message


class TestChatIntent:
    def test_greeting_is_chat_only(self):
        assert is_chat_only_message("你好")
        assert is_chat_only_message("您好！")

    def test_capability_question_is_chat_only(self):
        assert is_chat_only_message("你能帮我做什么")
        assert is_chat_only_message("你有什么功能")

    def test_alarm_query_not_chat_only(self):
        assert not is_chat_only_message("查近三天告警")
        assert not is_chat_only_message("查看近三天报警记录")

    def test_greeting_plus_action_not_chat_only(self):
        assert not is_chat_only_message("你好，帮我查告警")

    def test_navigate_not_chat_only(self):
        assert not is_chat_only_message("请先跳转到告警管理页面")
