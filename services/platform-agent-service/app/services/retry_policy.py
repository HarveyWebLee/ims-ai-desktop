"""
统一工具失败重试与 Re-plan 策略（Phase B）。

文件职责
--------
把「工具失败 → 是否重试 → 如何 Re-plan → 如何流式告诉前端」收敛成一套可复用逻辑，
避免 plan_executor 与 agent_tool_retry 各自维护一份重试计数与事件格式。

在 Agent 流程中的位置
--------------------
工具执行路径上的「失败恢复层」：
  某工具 tool_end 失败（且非用户取消）
    → collect_stream_tool_outcome 解析结果
    → can_retry / emit_replan / build_replan_after_failure（task_planner）
    → 再次 run_once
    → 成功则结束；耗尽则 yield_text_chunks 输出友好提示

如何被调用
----------
- plan 编排执行器 / agent_tool_retry：``run_with_replan_retry``
- 观察单次流：``collect_stream_tool_outcome`` / ``observe_tool_end``
- 重试轮次标记：``forward_with_retry_tags``（给 tool_start/tool_end 打 retry）

白话解释
--------
像「自动补考」：第一次考试（工具调用）挂了，通知前端「我换套复习计划（replan）」，
再考一次；若用户自己点了取消，就不补考，直接把取消说明播出去。
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from typing import Any

from app.services.task_planner import (
    MAX_REPLAN_ATTEMPTS,
    build_replan_after_failure,
    parse_tool_result,
)

# 与 task_planner 保持一致，供外部引用（避免调用方再 import 两处常量）
MAX_TOOL_RETRY_PER_TURN = MAX_REPLAN_ATTEMPTS

# 单步工具多次失败时的用户提示（按工具名定制；未知工具走通用文案）
SINGLE_STEP_FAILURE_HINTS: dict[str, str] = {
    "query_alarms": "查询多次失败，请检查网络或登录状态后重试。",
    "download_file": "导出多次失败，请稍后重试或联系管理员。",
}


def can_retry(attempt: int) -> bool:
    """
    当前 attempt 是否仍允许进入（含）Re-plan 重试。

    约定:
        attempt=0 为首次执行；失败后 attempt 递增；
        当 attempt > MAX_REPLAN_ATTEMPTS 时不再重试。
    """
    return attempt <= MAX_REPLAN_ATTEMPTS


def failure_hint(tool_name: str) -> str:
    """按工具名返回失败兜底提示文案（耗尽重试后展示给用户）。"""
    return SINGLE_STEP_FAILURE_HINTS.get(
        tool_name,
        "操作多次失败，请稍后重试或联系管理员。",
    )


def observe_tool_end(payload: dict[str, Any]) -> tuple[bool, str, bool]:
    """
    从 tool_end SSE payload 解析工具是否成功、摘要及是否应停止重试。

    返回:
        (ok, summary, stop_retry)
        - stop_retry=True：用户取消或权限拒绝等，上层不得自动重试 / Re-plan
    """
    ok, summary, stop_retry, _user_cancelled = parse_tool_result(str(payload.get("result", "")))
    return ok, summary, stop_retry


async def yield_text_chunks(
    text: str,
    *,
    chunk_size: int = 12,
    delay: float = 0.02,
) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    """
    将文本拆块流式输出 message 事件（打字机效果）。

    用于 replan 原因说明、取消说明、失败兜底提示等非 tool 文本。
    """
    for i in range(0, len(text), chunk_size):
        yield ("message", {"type": "text", "delta": text[i : i + chunk_size]})
        await asyncio.sleep(delay)


async def emit_replan(
    *,
    reason: str,
    steps: list[dict[str, Any]],
    attempt: int,
    failed_tool: str,
    source: str | None = None,
) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    """
    产出 replan 事件及原因说明文本流。

    前端收到 event:replan 后更新 TaskProgress 步骤；随后的 message 片段展示原因。
    """
    payload: dict[str, Any] = {
        "reason": reason,
        "steps": steps,
        "attempt": attempt,
        "failed_tool": failed_tool,
    }
    if source:
        payload["source"] = source
    yield ("replan", payload)
    async for evt in yield_text_chunks(f"\n\n**{reason}**\n"):
        yield evt


async def forward_with_retry_tags(
    stream: AsyncIterator[tuple[str, dict[str, Any]]],
    *,
    is_retry: bool,
    attempt: int,
) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    """
    透传事件流；重试轮次在 tool_start/tool_end 上附加 retry / attempt 标记。

    便于前端区分「首次工具调用」与「补考那一次」的时间线。
    """
    async for evt in stream:
        if is_retry and evt[0] in ("tool_start", "tool_end"):
            payload = dict(evt[1])
            payload["retry"] = True
            payload["attempt"] = attempt
            yield (evt[0], payload)
        else:
            yield evt


async def run_stream_until_tool_result(
    stream: AsyncIterator[tuple[str, dict[str, Any]]],
    *,
    watch_tool: str | None = None,
    skip_retry_ends: bool = False,
) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    """
    透传事件流占位（历史 API）。

    真正「收集事件 + 解析工具成败」请用 ``collect_stream_tool_outcome``。
    """
    async for evt in stream:
        yield evt


async def collect_stream_tool_outcome(
    stream: AsyncIterator[tuple[str, dict[str, Any]]],
    *,
    watch_tool: str | None = None,
    skip_retry_ends: bool = False,
) -> tuple[list[tuple[str, dict[str, Any]]], bool, str, str | None, dict[str, Any], bool]:
    """
    消费事件流，收集全部事件并解析目标工具执行结果。

    业务规则:
        - 用 tool_start 记住各工具的 args，失败时带回 failed_args 方便重试
        - skip_retry_ends：忽略已带 retry 标记的 tool_end（避免二次统计）
        - watch_tool：只关心某个工具名的结局；其它 tool_end 跳过
        - 用户取消：立刻 break，不再等后续事件

    返回:
        (events, tool_ok, error_summary, failed_tool, failed_args, user_cancelled)
    """
    events: list[tuple[str, dict[str, Any]]] = []
    # tool 名 → 最近一次 tool_start 的参数（供失败时回传）
    pending_args: dict[str, dict[str, Any]] = {}
    tool_ok = True
    error_summary = ""
    failed_tool: str | None = None
    failed_args: dict[str, Any] = {}
    user_cancelled = False

    async for evt in stream:
        events.append(evt)
        name, payload = evt

        if name == "tool_start":
            tool = str(payload.get("tool", ""))
            pending_args[tool] = dict(payload.get("args") or {})

        if name == "tool_end":
            tool = str(payload.get("tool", ""))
            # 业务规则：跳过「补考标记」的 end，避免把重试过程当最终结果
            if skip_retry_ends and payload.get("retry"):
                continue
            # 业务规则：只观测指定工具（如本轮要盯 download_file）
            if watch_tool and tool != watch_tool:
                continue
            ok, summary, cancelled = observe_tool_end(payload)
            if cancelled:
                # 用户主动取消：不当作可重试失败
                user_cancelled = True
                tool_ok = False
                error_summary = summary
                failed_tool = tool
                failed_args = pending_args.get(tool, {})
                break
            if not ok:
                tool_ok = False
                error_summary = summary
                failed_tool = tool
                failed_args = pending_args.get(tool, {})

    return events, tool_ok, error_summary, failed_tool, failed_args, user_cancelled


async def run_with_replan_retry(
    run_once: Callable[[int, bool], AsyncIterator[tuple[str, dict[str, Any]]]],
    *,
    plan_steps: list[dict[str, Any]],
    failed_tool: str,
    user_message: str,
    on_failure_hint: str | None = None,
) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    """
    通用 Re-plan 重试循环：首次执行 → 失败则 emit replan → 重试。

    参数:
        run_once: (attempt, is_retry) -> 事件流；attempt=0 为首次
        plan_steps: 当前计划步骤（会被 replan 更新）
        failed_tool: 观测目标工具名（传给 collect 的 watch_tool）
        user_message: 用户原话（生成恢复计划标签时需要）
        on_failure_hint: 耗尽重试后的提示文案；缺省走 failure_hint(tool)

    事件语义（给小白）:
        1. 第一次跑完整条事件流
        2. 若 tool_ok → 直接结束
        3. 若用户取消 → 输出取消文案后结束（不 Re-plan）
        4. 若失败且还可重试 → 发 replan + 新 steps，再跑一遍
        5. 次数用尽 → 输出兜底提示
    """
    steps = list(plan_steps)
    attempts = 0
    last_error = ""

    while can_retry(attempts):
        # attempts>0：说明上一轮失败，先通知前端「换计划」再开跑
        if attempts > 0:
            replan_steps, reason = build_replan_after_failure(
                original_steps=steps,
                failed_tool=failed_tool,
                error_summary=last_error,
                user_message=user_message,
            )
            steps = replan_steps
            async for evt in emit_replan(
                reason=reason,
                steps=replan_steps,
                attempt=attempts,
                failed_tool=failed_tool,
            ):
                yield evt

        stream = run_once(attempts, attempts > 0)
        # 重试轮给 tool_* 打标记，便于 Trace / UI 区分
        events, tool_ok, last_error, _, _, user_cancelled = await collect_stream_tool_outcome(
            forward_with_retry_tags(
                stream,
                is_retry=attempts > 0,
                attempt=attempts,
            )
            if attempts > 0
            else stream,
            watch_tool=failed_tool,
        )
        for evt in events:
            yield evt

        # 对称路径：用户取消 → 不进入 Re-plan
        if user_cancelled:
            async for evt in yield_text_chunks(f"\n\n{last_error or '已取消操作。'}"):
                yield evt
            return

        if tool_ok:
            return

        attempts += 1
        if not can_retry(attempts):
            hint = on_failure_hint or failure_hint(failed_tool)
            async for evt in yield_text_chunks(f"\n\n{hint}"):
                yield evt
            return
