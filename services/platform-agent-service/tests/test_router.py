"""Phase A 编排层单测"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.graph.context import assemble_context
from app.graph.router import TaskRoute, classify_task
from app.services.prompt_assembly import build_system_prompt, extract_user_display_message


@pytest.fixture(autouse=True)
def _disable_rag_injection():
    """单测不连本机 Qdrant，避免知识库命中污染 llm_user_message 断言。"""
    with patch("app.rag.context.retrieve_knowledge_blocks", return_value=[]):
        yield


class TestRouter:
    def test_classify_llm_for_tool_intent(self):
        ctx = assemble_context(thread_id="t1", message="查看近三天报警记录")
        assert classify_task(ctx) == TaskRoute.LLM

    def test_classify_chat_when_greeting(self):
        ctx = assemble_context(thread_id="t1", message="你好")
        assert classify_task(ctx) == TaskRoute.CHAT

    def test_classify_chat_when_capability_question(self):
        ctx = assemble_context(thread_id="t1", message="你能帮我做什么")
        assert classify_task(ctx) == TaskRoute.CHAT

    def test_classify_llm_when_greeting_with_action(self):
        ctx = assemble_context(thread_id="t1", message="你好，查近三天告警")
        assert classify_task(ctx) == TaskRoute.LLM


class TestContext:
    def test_assemble_injects_path_into_llm_message(self):
        ctx = assemble_context(
            thread_id="t1",
            message="导出近三天",
            metadata={"current_path": "/config_management/config/alarm_info_query"},
            recent_user_messages=["你好"],
        )
        assert ctx.current_path == "/config_management/config/alarm_info_query"
        assert "使用者当前页面路径" in ctx.llm_user_message
        assert "导出近三天" in ctx.llm_user_message
        assert "你好" in ctx.llm_user_message

    def test_assemble_plain_message(self):
        ctx = assemble_context(thread_id="t2", message="打开设备管理")
        assert ctx.llm_user_message == "打开设备管理"

    def test_assemble_door_control_forces_tool_hint(self):
        ctx = assemble_context(thread_id="t3", message="帮我开门")
        assert "send_device_cmd" in ctx.llm_user_message
        assert 'action="开门"' in ctx.llm_user_message
        assert "禁止" in ctx.llm_user_message
        assert "正在等待执行结果" in ctx.llm_user_message  # 反幻觉约束文案
        assert extract_user_display_message(ctx.llm_user_message) == "帮我开门"

    def test_assemble_broadcast_with_device_and_content_hints(self):
        msg = "给 icpas101 播放广播，内容为你好"
        ctx = assemble_context(thread_id="t-bc", message=msg)
        assert "send_device_cmd" in ctx.llm_user_message
        assert 'action="播报"' in ctx.llm_user_message
        assert "icpas101" in ctx.llm_user_message
        assert "variable_value" in ctx.llm_user_message
        assert "你好" in ctx.llm_user_message
        assert "正在等待执行结果" in ctx.llm_user_message
        assert extract_user_display_message(ctx.llm_user_message) == msg

    def test_assemble_device_control_skips_passive_rag(self):
        """设备控制意图不得注入被动 RAG，避免前端播报方案文档污染。"""
        fake_blocks = [
            {
                "text": "报警提醒播报功能实现方案 resumeBroadcast",
                "source": "prj-docs/alarm_query_statistics.md",
                "score": 0.9,
            }
        ]
        with patch(
            "app.rag.context.retrieve_knowledge_blocks",
            return_value=fake_blocks,
        ) as mock_rag:
            ctx = assemble_context(
                thread_id="t-rag-skip",
                message="给 icpas101 播放广播，内容为你好",
            )
            mock_rag.assert_not_called()
            assert "参考知识" not in ctx.llm_user_message
            assert "resumeBroadcast" not in ctx.llm_user_message

    def test_assemble_generic_dispatch_forces_tool_without_door_default(self):
        ctx = assemble_context(thread_id="t-generic", message="给设备下发指令")
        assert "send_device_cmd" in ctx.llm_user_message
        assert "任意具备可写变量" in ctx.llm_user_message
        assert 'action="开门"' not in ctx.llm_user_message
        assert extract_user_display_message(ctx.llm_user_message) == "给设备下发指令"

    def test_classify_llm_when_open_door(self):
        ctx = assemble_context(thread_id="t1", message="帮我开门")
        assert classify_task(ctx) == TaskRoute.LLM

    def test_conditional_inspect_then_control_no_door_hint(self):
        """条件句「先查状态再分支控制」不应注入强制 send_device_cmd 提示。"""
        msg = (
            "查看716门禁[172.168.1.42]设备的状态，如果在线就下发开门指令，如果离线就查看其历史数据"
        )
        ctx = assemble_context(thread_id="t-cond", message=msg)
        assert "send_device_cmd" not in ctx.llm_user_message
        assert "设备控制意图" not in ctx.llm_user_message
        assert extract_user_display_message(ctx.llm_user_message) == msg

    def test_colloquial_online_offline_branch_no_door_hint(self):
        """口语「在线开门，离线查历史」也不应被劫持为纯开门意图。"""
        msg = "查716门禁，在线开门，离线查历史"
        ctx = assemble_context(thread_id="t-cond2", message=msg)
        assert "设备控制意图" not in ctx.llm_user_message
        assert extract_user_display_message(ctx.llm_user_message) == msg


class TestPromptAssembly:
    def test_system_prompt_contains_core_sections(self):
        prompt = build_system_prompt()
        assert "综合信息平台" in prompt
        assert "意图识别与工具调用" in prompt or "意图 → 工具" in prompt
        assert "已注册工具与平台接口" in prompt
        assert "当前时间" in prompt
        assert "query_alarms" in prompt

    def test_system_prompt_no_duplicate_param_tables(self):
        """精简后不在 prompt 重复完整参数表（由 tool Schema 提供）。"""
        prompt = build_system_prompt()
        assert "### 3.1 `query_alarms`" not in prompt
        assert prompt.count("| 参数 | 必填 | 说明 |") == 0

    def test_prompt_length_reasonable(self):
        prompt = build_system_prompt()
        # 精简后应明显短于旧版 ~150 行 intent 全文 + 重复参数表
        assert len(prompt) < 13000

    def test_extract_user_display_message_strips_context(self):
        llm_text = assemble_context(
            thread_id="t1",
            message="接下来告诉我本年7月份的告警统计数量",
            metadata={"current_path": "/config_management/config/alarm_info_query"},
            recent_user_messages=["你好", "请先跳转到告警管理页面"],
        ).llm_user_message
        assert extract_user_display_message(llm_text) == "接下来告诉我本年7月份的告警统计数量"

    def test_extract_user_display_message_plain(self):
        assert extract_user_display_message("打开设备管理") == "打开设备管理"

    def test_build_chat_direct_prompt_has_no_tool_catalog(self):
        from app.services.prompt_assembly import build_chat_direct_system_prompt

        prompt = build_chat_direct_system_prompt()
        assert "对话模式" in prompt
        assert "已注册工具与平台接口" not in prompt
        assert "intent_and_tools" not in prompt
