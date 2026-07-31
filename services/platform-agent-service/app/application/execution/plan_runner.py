"""显式 Plan 的逐步执行策略。"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from typing import Any, Protocol

from app.application.execution.common import ExecuteState, is_task_complete
from app.application.execution.tool_executor import execute_tool_invoke
from app.services.retry_policy import (
    can_retry,
    emit_replan,
    failure_hint,
    yield_text_chunks,
)
from app.services.task_planner import build_replan_after_failure, parse_tool_result


class ToolInvoke(Protocol):
    """工具执行异步流签名。"""

    def __call__(
        self,
        tool_name: str,
        args: dict[str, Any] | None,
        *,
        retry: bool = False,
        attempt: int = 0,
        auth_token: str | None = None,
        thread_id: str | None = None,
        hitl_confirm_bypass: bool = False,
    ) -> AsyncIterator[tuple[str, dict[str, Any]]]: ...


async def execute_planned_step(
    step: dict[str, Any],
    params: dict[str, Any],
    *,
    attempt: int = 0,
    is_retry: bool = False,
    auth_token: str | None = None,
    thread_id: str | None = None,
    execute_tool_invoke_fn: ToolInvoke | None = None,
) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    """执行单个 Plan 步骤。"""
    tool_invoke_fn = execute_tool_invoke_fn or execute_tool_invoke
    tool_name = str(step.get("tool") or "")
    if not tool_name:
        return

    async for event in tool_invoke_fn(
        tool_name,
        params,
        retry=is_retry,
        attempt=attempt,
        auth_token=auth_token,
        thread_id=thread_id,
    ):
        yield event


async def execute_plan_steps(
    plan_steps: list[dict[str, Any]],
    params_by_tool: dict[str, dict[str, Any]],
    user_message: str,
    *,
    thread_id: str = "",
    auth_token: str | None = None,
    stream_step: Callable[
        [dict[str, Any], dict[str, Any], str],
        AsyncIterator[tuple[str, dict[str, Any]]],
    ]
    | None = None,
    execute_tool_invoke_fn: ToolInvoke | None = None,
) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    """按 Plan 顺序逐步执行，单步失败走统一 Re-plan 重试。"""
    tool_invoke_fn = execute_tool_invoke_fn or execute_tool_invoke
    steps = list(plan_steps)
    state = ExecuteState(plan_steps=steps)
    from platform_mcp.runtime.context import current_thread_id

    effective_thread_id = (thread_id or current_thread_id.get() or "").strip()

    for step in steps:
        if step.get("status") not in ("pending", "running"):
            continue
        tool_name = str(step.get("tool") or "")
        if not tool_name:
            continue
        from app.services.plan_confirm import resolve_step_tool_params

        params = resolve_step_tool_params(step, params_by_tool, user_message)

        async def _run_once(
            attempt: int,
            is_retry: bool,
            *,
            _step: dict[str, Any] = step,
            _tool: str = tool_name,
            _params: dict[str, Any] = params,
        ) -> AsyncIterator[tuple[str, dict[str, Any]]]:
            _ = _tool
            if stream_step is not None:
                async for event in stream_step(_step, _params, user_message):
                    if is_retry and event[0] in ("tool_start", "tool_end"):
                        payload = dict(event[1])
                        payload["retry"] = True
                        payload["attempt"] = attempt
                        yield (event[0], payload)
                    else:
                        yield event
                return
            async for event in execute_planned_step(
                _step,
                _params,
                attempt=attempt,
                is_retry=is_retry,
                auth_token=auth_token,
                thread_id=effective_thread_id or None,
                execute_tool_invoke_fn=tool_invoke_fn,
            ):
                yield event

        tool_ok = True
        attempts = 0
        last_error = ""

        while can_retry(attempts):
            if attempts > 0:
                replan_steps, reason = build_replan_after_failure(
                    original_steps=steps,
                    failed_tool=tool_name,
                    error_summary=last_error,
                    user_message=user_message,
                    failed_args=params,
                )
                steps = replan_steps
                state.plan_steps = steps
                async for event in emit_replan(
                    reason=reason,
                    steps=replan_steps,
                    attempt=attempts,
                    failed_tool=tool_name,
                ):
                    yield event

            tool_ok = True
            async for event in _run_once(attempts, attempts > 0):
                if event[0] == "error":
                    yield event
                    return
                if event[0] == "interrupt":
                    state.interrupted = True
                    yield event
                    return
                if event[0] == "tool_end" and event[1].get("tool") == tool_name:
                    ok, last_error, stop_retry, user_cancelled = parse_tool_result(
                        str(event[1].get("result") or "")
                    )
                    state.record_tool_end(ok=ok)
                    tool_ok = ok
                    if user_cancelled:
                        step["status"] = "skipped"
                        async for hint_event in yield_text_chunks(
                            f"\n\n{last_error or '已取消操作。'}"
                        ):
                            yield hint_event
                        return
                    if stop_retry:
                        # 权限/不可重试：不 Re-plan
                        step["status"] = "error"
                        async for hint_event in yield_text_chunks(
                            f"\n\n{last_error or '操作失败，已停止自动重试。'}"
                        ):
                            yield hint_event
                        return
                yield event

            if tool_ok:
                step["status"] = "done"
                params_by_tool[tool_name] = dict(params)
                if tool_name == "query_alarms":
                    from app.services.plan_confirm import propagate_query_alarm_filter_params

                    propagate_query_alarm_filter_params(params_by_tool, steps)
                break

            attempts += 1
            if not can_retry(attempts):
                step["status"] = "error"
                hint = failure_hint(tool_name)
                async for event in yield_text_chunks(f"\n\n{hint}"):
                    yield event
                return

        if is_task_complete(state):
            return
