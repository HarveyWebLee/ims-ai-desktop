"""Phase B 统一执行循环单测"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from platform_mcp.runtime.context import current_auth_token

from app.application.execution import (
    ExecuteState,
    emit_tool_events,
    execute_plan_steps,
    execute_tool_invoke,
    is_task_complete,
    run_agent_stream,
)
from app.services.retry_policy import (
    can_retry,
    emit_replan,
    observe_tool_end,
)
from app.services.task_planner import parse_tool_result


class TestParseToolResult:
    def test_user_cancelled_flag(self):
        ok, summary, stop_retry, cancelled = parse_tool_result(
            json.dumps({"ok": False, "summary": "使用者已取消导出。", "user_cancelled": True})
        )
        assert ok is False
        assert stop_retry is True
        assert cancelled is True
        assert "取消" in summary

    def test_non_retryable_is_not_user_cancelled(self):
        """硬失败 stop_retry=True，但不得当作 user_cancelled（避免 Plan 标 skipped）。"""
        ok, summary, stop_retry, cancelled = parse_tool_result(
            json.dumps(
                {
                    "ok": False,
                    "summary": "该设备未配置变量 play（播报），可能不是广播设备或不支持远程播报。",
                    "data": {"non_retryable": True, "failure_kind": "required_var_unsupported"},
                }
            )
        )
        assert ok is False
        assert stop_retry is True
        assert cancelled is False
        assert "play" in summary


class TestEmitToolEvents:
    def test_basic_tool_pair(self):
        events = emit_tool_events("query_alarms", {"start_time": "近三天"}, '{"ok": true}')
        assert len(events) == 2
        assert events[0][0] == "tool_start"
        assert events[1][0] == "tool_end"
        assert events[0][1]["tool"] == "query_alarms"

    def test_retry_tags(self):
        events = emit_tool_events("query_alarms", {}, "{}", retry=True, attempt=1)
        assert events[0][1]["retry"] is True
        assert events[0][1]["attempt"] == 1


class TestObserveToolEnd:
    def test_ok_false(self):
        ok, summary, cancelled = observe_tool_end(
            {"result": json.dumps({"ok": False, "summary": "网络错误"})}
        )
        assert ok is False
        assert summary == "网络错误"
        assert cancelled is False

    def test_user_cancelled(self):
        ok, summary, cancelled = observe_tool_end(
            {
                "result": json.dumps(
                    {"ok": False, "summary": "使用者已取消导出。", "user_cancelled": True}
                )
            }
        )
        assert ok is False
        assert cancelled is True

    def test_permission_denied_stops_retry(self):
        ok, summary, stop_retry = observe_tool_end(
            {
                "result": json.dumps(
                    {
                        "ok": False,
                        "summary": "当前用户缺少工具权限：alarm:confirm",
                        "data": {
                            "error_code": "tool_permission_denied",
                            "non_retryable": True,
                        },
                    }
                )
            }
        )
        assert ok is False
        assert stop_retry is True
        assert "权限" in summary

    def test_ok_true(self):
        ok, _, cancelled = observe_tool_end({"result": json.dumps({"ok": True, "summary": "成功"})})
        assert ok is True
        assert cancelled is False


class TestEmptyToolResultClosesToolEnd:
    @pytest.mark.asyncio
    async def test_empty_result_still_emits_tool_end(self):
        """已发出 tool_start 后，空结果也必须闭合 tool_end，避免 Plan 卡在 running。"""
        from app.application.tool_execution import (
            PreparedToolExecution,
            ToolExecutionOutcome,
        )
        from app.domain.tool_execution import ToolExecutionRequest

        class EmptyResultPipeline:
            async def prepare(self, request: ToolExecutionRequest) -> PreparedToolExecution:
                return PreparedToolExecution(request=request)

            async def invoke(
                self,
                prepared: PreparedToolExecution,
                *,
                hitl_confirm_bypass: bool = False,
            ) -> ToolExecutionOutcome:
                return ToolExecutionOutcome(result="")

        events: list[tuple[str, dict]] = []
        with patch(
            "app.application.execution.tool_executor.get_tool_execution_pipeline",
            return_value=EmptyResultPipeline(),
        ):
            async for event in execute_tool_invoke(
                "query_devices",
                {"device_name": "一号泵"},
                auth_token="Bearer test",
                thread_id="thread-empty-result",
            ):
                events.append(event)

        assert [name for name, _ in events] == ["tool_start", "tool_end"]
        result = json.loads(events[-1][1]["result"])
        assert result["ok"] is False
        assert result["data"]["error_code"] == "empty_tool_result"


class TestTaskComplete:
    def test_interrupt(self):
        state = ExecuteState(interrupted=True)
        assert is_task_complete(state, llm_idle=True) is True

    def test_plan_all_done(self):
        state = ExecuteState(
            plan_steps=[
                {"id": "1", "status": "done"},
                {"id": "2", "status": "skipped"},
            ]
        )
        assert is_task_complete(state) is True

    def test_llm_idle(self):
        state = ExecuteState()
        assert is_task_complete(state, llm_idle=True) is True

    def test_llm_idle_blocked_by_active_plan(self):
        """显式 Plan 仍有 pending/running 时不因 LLM 输出文本提前结束。"""
        state = ExecuteState(
            plan_steps=[
                {"id": "1", "status": "done"},
                {"id": "2", "status": "pending"},
            ]
        )
        assert is_task_complete(state, llm_idle=True) is False

    def test_llm_idle_blocked_by_awaiting_confirm(self):
        state = ExecuteState(plan_steps=[{"id": "1", "status": "awaiting_confirm"}])
        assert is_task_complete(state, llm_idle=True) is False

    def test_llm_idle_blocked_by_awaiting_hitl(self):
        """Plan 步骤 awaiting_hitl 时不应提前结束。"""
        state = ExecuteState(plan_steps=[{"id": "1", "status": "awaiting_hitl"}])
        assert is_task_complete(state, llm_idle=True) is False

    def test_step_limit(self):
        from app.application.execution import MAX_EXECUTE_STEPS

        state = ExecuteState(tool_step_count=MAX_EXECUTE_STEPS)
        assert is_task_complete(state) is True


class TestRetryPolicy:
    def test_can_retry_bounds(self):
        assert can_retry(0) is True
        assert can_retry(1) is True
        assert can_retry(2) is False


class TestExecutePlanSteps:
    @pytest.mark.asyncio
    async def test_runs_steps_in_order(self):
        calls: list[str] = []

        async def mock_stream(step, params, user_message):
            tool = step["tool"]
            calls.append(tool)
            yield (
                "tool_start",
                {"tool": tool, "args": params},
            )
            yield (
                "tool_end",
                {
                    "tool": tool,
                    "result": json.dumps({"ok": True, "summary": "ok"}),
                },
            )

        plan = [
            {"id": "1", "label": "查", "tool": "query_alarms", "status": "pending"},
            {"id": "2", "label": "导", "tool": "download_file", "status": "pending"},
        ]
        events = []
        async for evt in execute_plan_steps(
            plan,
            {
                "query_alarms": {"start_time": "近三天"},
                "download_file": {"resource": "alarm_report"},
            },
            "查近三天并导出",
            stream_step=mock_stream,
        ):
            events.append(evt)

        assert calls == ["query_alarms", "download_file"]
        assert any(e[0] == "tool_end" for e in events)

    @pytest.mark.asyncio
    async def test_multi_navigate_steps_use_distinct_paths(self):
        """连续 navigate_to 应使用各步骤 label 对应的路径。"""
        captured_args: list[dict] = []

        async def mock_stream(step, params, user_message):
            captured_args.append(dict(params))
            yield ("tool_start", {"tool": step["tool"], "args": params})
            yield (
                "tool_end",
                {
                    "tool": step["tool"],
                    "result": json.dumps({"ok": True, "summary": "ok"}),
                },
            )

        plan = [
            {"id": "1", "label": "跳转到设施页面，", "tool": "navigate_to", "status": "pending"},
            {"id": "2", "label": "跳转到设备变量，", "tool": "navigate_to", "status": "pending"},
        ]
        async for _ in execute_plan_steps(
            plan,
            {"navigate_to": {"path": "到设施页面"}},
            "先跳转到设施页面，然后跳转到设备变量",
            stream_step=mock_stream,
        ):
            pass

        assert len(captured_args) == 2
        assert captured_args[0]["path"] == "设施页面"
        assert captured_args[1]["path"] == "设备变量"


class TestHitlConfirmBypass:
    @pytest.mark.asyncio
    async def test_bypass_propagates_via_explicit_param(self):
        """hitl_confirm_bypass=True 时工具 invoke 不应再抛 confirm。"""
        from platform_mcp.runtime.hitl import McpHitlSignal

        async def fake_invoke(tool_name: str, args: dict) -> str:
            from platform_mcp.runtime.context import current_hitl_confirm_bypass

            if not current_hitl_confirm_bypass.get():
                raise McpHitlSignal({"type": "confirm", "tool": tool_name, "message": "需要确认"})
            return json.dumps({"ok": True, "summary": "已导出"})

        with patch(
            "app.services.agent_tool_retry.invoke_tool_async",
            side_effect=fake_invoke,
        ):
            with patch("platform_mcp.runtime.tool_preflight.preflight_tool") as mock_preflight:
                from platform_mcp.runtime.tool_preflight import PreflightResult

                mock_preflight.return_value = PreflightResult(
                    args={"resource": "alarm_report"},
                    interrupt=None,
                )
                events = []
                async for evt in execute_tool_invoke(
                    "download_file",
                    {"resource": "alarm_report"},
                    hitl_confirm_bypass=True,
                ):
                    events.append(evt)

        assert not any(e[0] == "interrupt" for e in events)
        assert any(e[0] == "tool_end" for e in events)


class TestRunAgentStream:
    @pytest.mark.asyncio
    async def test_delegates_to_parent_graph_stream(self):
        async def fake_stream(**_kwargs):
            yield ("message", {"type": "text", "delta": "hi"})
            yield (
                "tool_end",
                {
                    "tool": "query_alarms",
                    "result": json.dumps({"ok": True, "summary": "5条"}),
                },
            )

        with patch(
            "app.graph.parent_graph_stream.stream_parent_graph",
            side_effect=fake_stream,
        ):
            events = []
            async for evt in run_agent_stream(
                thread_id="t1",
                model_id="deepseek-chat",
                input_payload={"messages": []},
            ):
                events.append(evt)

        assert ("message", {"type": "text", "delta": "hi"}) in events

    @pytest.mark.asyncio
    async def test_passthrough_user_cancelled_without_replan(self):
        """用户取消工具时透传事件，不注入旁路 replan。"""

        async def fake_stream(**_kwargs):
            yield (
                "tool_start",
                {"tool": "download_file", "args": {"resource": "alarm_report"}},
            )
            yield (
                "tool_end",
                {
                    "tool": "download_file",
                    "result": json.dumps(
                        {
                            "ok": False,
                            "summary": "使用者已取消导出。",
                            "user_cancelled": True,
                        }
                    ),
                },
            )

        with patch(
            "app.graph.parent_graph_stream.stream_parent_graph",
            side_effect=fake_stream,
        ):
            events = []
            async for evt in run_agent_stream(
                thread_id="t1",
                model_id="deepseek-chat",
                input_payload={"messages": []},
            ):
                events.append(evt)

        assert not any(e[0] == "replan" for e in events)
        retry_starts = [e for e in events if e[0] == "tool_start" and e[1].get("retry")]
        assert len(retry_starts) == 0


class TestExecuteToolInvokeAuthContext:
    @pytest.mark.asyncio
    async def test_auth_token_visible_during_tool_invoke(self):
        """Plan 逐步执行时 JWT 应透传到工具调用上下文。"""
        seen_auth: list[str | None] = []
        auth_token = current_auth_token.set("Bearer test-jwt")
        try:

            async def fake_invoke(tool_name: str, args: dict):
                seen_auth.append(current_auth_token.get())
                return json.dumps({"ok": True, "summary": f"{tool_name} ok"})

            events = []
            with patch(
                "app.services.agent_tool_retry.invoke_tool_async",
                side_effect=fake_invoke,
            ):
                async for evt in execute_tool_invoke(
                    "query_alarms",
                    {"start_time": "近三天"},
                ):
                    events.append(evt)

            assert seen_auth == ["Bearer test-jwt"]
            assert any(e[0] == "tool_end" for e in events)
        finally:
            current_auth_token.reset(auth_token)


class TestEmitReplan:
    @pytest.mark.asyncio
    async def test_replan_event(self):
        events = []
        async for evt in emit_replan(
            reason="重试",
            steps=[{"id": "1", "tool": "query_alarms", "status": "pending"}],
            attempt=1,
            failed_tool="query_alarms",
        ):
            events.append(evt)
        assert events[0][0] == "replan"
        assert events[0][1]["failed_tool"] == "query_alarms"
