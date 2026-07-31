"""
SSE 流包装器：注入 Plan 更新、Re-plan 与 Trace 事件

文件职责
--------
作为 `stream_chat` / `stream_resume` 的「装饰层」，
在原始 SSE 事件流外包一层，额外产出：
- plan / plan_update：TaskProgress 多步计划
- replan：工具失败后的恢复计划（auto_replan=True 时）
- trace：TracePanel 实时事件
并在流结束时持久化 trace、关键事件写入 audit_store。

在 Agent 流程中的位置
--------------------
  stream_chat_core / _resume_inner（内层事件）
    → wrap_stream_with_plan_trace（本文件）
      → chat.py / resume.py `_format_sse` → 浏览器

关键概念（白话）
----------------
- PlanTracker：记「第几步、成功/失败/等人确认」，跟 tool_start/end 对齐。
- 动态 Plan：没预生成步骤时，第一次 tool_start 才开始往 TaskProgress 加步。
- suppressed tools：新意图开始后禁止把「上一轮残留工具 SSE」透传给 UI。
- auto_replan=False：Re-plan 由 Plan 执行路径 emit；envelope 默认同步 tracker。

核心类:
    PlanTracker — 跟踪步骤状态；无预生成 Plan 时在首次 tool_start 动态追加
"""

# ---------------------------------------------------------------------------
# 标准库
# ---------------------------------------------------------------------------
from __future__ import annotations

import copy
from collections.abc import AsyncIterator
from typing import Any

# ---------------------------------------------------------------------------
# 本项目：审计、计划、Trace
# ---------------------------------------------------------------------------
from app.services.audit_store import audit_store, build_audit_from_sse
from app.services.task_planner import (
    MAX_REPLAN_ATTEMPTS,
    build_replan_after_failure,
    parse_tool_result,
)
from app.services.trace_collector import TraceCollector
from app.services.trace_store import trace_store


def _tool_step_label(
    tool_name: str,
    *,
    user_message: str = "",
    tool_args: dict[str, Any] | None = None,
) -> str:
    """
    工具名 → 中文步骤标签（动态 Plan 展示用）。

    参数:
        tool_name: 如 "query_alarms"
        user_message: 用户原话（download_file 按 resource 区分标签）
        tool_args: 工具调用参数（优先取 resource）

    返回:
        中文描述，未知工具则返回原名
    """
    if tool_name == "download_file":
        from app.services.task_planner import (
            _resolve_download_resource,
            download_export_step_label,
        )

        return download_export_step_label(
            user_message,
            resource=_resolve_download_resource(
                user_message=user_message,
                failed_args=tool_args,
            ),
        )
    labels = {
        "query_alarms": "查询告警数据",
        "navigate_to": "页面导航",
        "pause": "停留等待",
        "get_alarm_detail": "查看告警详情",
        "open_alarm_detail": "打开告警详情",
        "batch_confirm_alarms": "批量确认告警",
        "batch_process_alarms": "批量处理告警",
    }
    return labels.get(tool_name, tool_name)


class PlanTracker:
    """
    跟踪多步计划状态并与工具调用对齐。

    状态流转:
        pending → running（tool_start）→ done/error（tool_end）
        失败 Re-plan 时 pending 步可能变为 skipped

    属性:
        steps: 当前计划步骤列表（dict 含 id/label/tool/status）
        replan_count: 已 Re-plan 次数
        last_replan_reason: 最近一次 Re-plan 原因文案
    """

    def __init__(
        self,
        steps: list[dict[str, Any]] | None,
        *,
        graph: dict[str, Any] | None = None,
        flow_document: dict[str, Any] | None = None,
        user_message: str = "",
    ) -> None:
        # deepcopy 避免修改传入的原始 list/dict
        self.steps = copy.deepcopy(steps) if steps else []
        self.graph = copy.deepcopy(graph) if graph else None
        self.flow_document = copy.deepcopy(flow_document) if flow_document else None
        self.user_message = user_message
        self._last_tool_args: dict[str, dict[str, Any]] = {}
        self._active_step_id: str | None = None  # 当前 running 的步骤 id
        self.replan_count = 0
        self.last_replan_reason: str = ""

    @property
    def has_plan(self) -> bool:
        """
        是否应向 UI 展示 TaskProgress。

        单步直达也展示（>= 1 步即 True）。
        """
        return len(self.steps) >= 1

    def initial_payload(self) -> dict[str, Any]:
        """返回 plan SSE 事件的 payload（steps + graph + 可选 flow_document）。"""
        from app.services.plan_graph import build_plan_sse_payload

        return build_plan_sse_payload(
            self.steps,
            graph=self.graph,
            flow_document=self.flow_document,
        )

    def replace_steps(self, steps: list[dict[str, Any]]) -> None:
        """用新步骤列表整体替换（Re-plan 后调用）。"""
        self.steps = copy.deepcopy(steps)

    def skip_pending_steps(self) -> list[dict[str, Any]]:
        """
        将未执行的 pending 步标记为 skipped（失败后中止后续步）。

        返回:
            plan_update 事件 payload 列表（每步一条）
        """
        updates: list[dict[str, Any]] = []
        for step in self.steps:
            if step.get("status") == "pending":
                step["status"] = "skipped"
                updates.append(
                    {
                        "step_id": str(step["id"]),
                        "status": "skipped",
                        "tool": step.get("tool"),
                    }
                )
        return updates

    def apply_external_plan_update(self, payload: dict[str, Any]) -> dict[str, Any]:
        """同步 BPMN 执行器下发的 plan_update（含 node_id / skipReason）。"""
        step_id = str(payload.get("step_id") or payload.get("node_id") or "")
        status = str(payload.get("status") or "")
        tool = payload.get("tool")
        skip_reason = payload.get("skipReason")
        node_type = payload.get("node_type")
        matched_branch = payload.get("matchedBranchKey")

        step: dict[str, Any] | None = None
        if step_id:
            for candidate in self.steps:
                if (
                    str(candidate.get("id")) == step_id
                    or str(candidate.get("nodeId") or "") == step_id
                ):
                    step = candidate
                    break
        if step is None and tool:
            step = self._find_step_for_tool(str(tool), include_awaiting_hitl=True)

        if step is None and step_id:
            step = {
                "id": step_id,
                "nodeId": step_id,
                "label": str(payload.get("label") or node_type or step_id),
                "status": status or "pending",
            }
            if tool:
                step["tool"] = tool
            if node_type:
                step["nodeType"] = node_type
            self.steps.append(step)
        elif step is not None and status:
            step["status"] = status
            if tool:
                step["tool"] = tool
            if skip_reason:
                step["skipReason"] = str(skip_reason)
            if matched_branch:
                step["matchedBranchKey"] = str(matched_branch)
            if node_type:
                step["nodeType"] = str(node_type)
            if step_id:
                step["nodeId"] = step_id

        return dict(payload)

    def _find_step_for_tool(
        self,
        tool_name: str,
        *,
        include_awaiting_hitl: bool = False,
    ) -> dict[str, Any] | None:
        """
        为工具调用查找对应 plan 步骤。

        优先匹配 tool 名相同且 status 为 pending/running（可选含 awaiting_hitl）的步；
        否则取第一个 pending 步。
        """
        active_statuses = ("pending", "running")
        if include_awaiting_hitl:
            active_statuses = ("pending", "running", "awaiting_hitl")
        for step in self.steps:
            if step.get("status") not in active_statuses:
                continue
            if step.get("tool") == tool_name:
                return step
        for step in self.steps:
            if step.get("status") == "pending":
                return step
        return None

    def on_tool_start(
        self,
        tool_name: str,
        tool_args: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """
        工具开始时更新步骤状态为 running。

        参数:
            tool_name: 开始的工具名
            tool_args: 工具调用参数（用于 download_file 步骤标签）

        返回:
            plan_update payload；动态新增步骤时同样返回 running 更新
        """
        if tool_name and tool_args:
            self._last_tool_args[tool_name] = dict(tool_args)
        step = self._find_step_for_tool(tool_name)
        if not step:
            # AI 意图路径：无预生成 Plan 时，按工具调用动态追加步骤
            next_id = str(len(self.steps) + 1)
            step = {
                "id": next_id,
                "label": _tool_step_label(
                    tool_name,
                    user_message=self.user_message,
                    tool_args=tool_args,
                ),
                "tool": tool_name,
                "status": "running",
            }
            self.steps.append(step)
            self._active_step_id = next_id
            return {"step_id": next_id, "status": "running", "tool": tool_name}
        step["status"] = "running"
        self._active_step_id = str(step["id"])
        return {
            "step_id": str(step["id"]),
            "status": "running",
            "tool": tool_name,
        }

    def on_tool_end(
        self,
        tool_name: str,
        *,
        ok: bool = True,
        user_cancelled: bool = False,
    ) -> dict[str, Any] | None:
        """
        工具结束时更新步骤状态为 done、error 或 skipped（用户取消）。

        参数:
            tool_name: 完成的工具名
            ok: 工具是否成功（parse_tool_result_ok 结果）
            user_cancelled: 使用者主动取消（HITL 拒绝），标 skipped 而非 error

        返回:
            plan_update payload，无法匹配步骤时返回 None
        """
        step_id = self._active_step_id
        active_tool = None
        if step_id:
            for step in self.steps:
                if str(step.get("id")) == step_id:
                    active_tool = step.get("tool")
                    break
        if not step_id or active_tool != tool_name:
            step = self._find_step_for_tool(
                tool_name,
                include_awaiting_hitl=True,
            )
            step_id = str(step["id"]) if step else None
        if not step_id:
            return None
        if user_cancelled:
            status = "skipped"
        else:
            status = "done" if ok else "error"
        for step in self.steps:
            if str(step["id"]) == step_id:
                step["status"] = status
                self._active_step_id = None
                return {
                    "step_id": str(step["id"]),
                    "status": status,
                    "tool": tool_name,
                }
        return None

    def on_interrupt(self, tool_name: str | None = None) -> list[dict[str, Any]]:
        """
        HITL 中断时将当前步骤标记为 awaiting_hitl（非 error）。

        工具因 interrupt() 暂停时，尚未真正失败，需等待使用者补参或确认。
        interrupt 声明的工具优先于 _active_step_id，避免 export 步误标导航 HITL。
        若 active 步为误触发的 download_file（running），先标 skipped；其它工具不自动 skipped。
        """
        updates: list[dict[str, Any]] = []
        # 仅跳过误触发的 download_file（导航 HITL 场景）；其它 running 工具不得标 skipped，
        # 否则会把已成功的 get_device_detail 等步误标为「已跳过」。
        if self._active_step_id and tool_name:
            for candidate in self.steps:
                if str(candidate.get("id")) == self._active_step_id:
                    if (
                        candidate.get("tool") != tool_name
                        and candidate.get("status") == "running"
                        and candidate.get("tool") == "download_file"
                    ):
                        candidate["status"] = "skipped"
                        updates.append(
                            {
                                "step_id": str(candidate["id"]),
                                "status": "skipped",
                                "tool": candidate.get("tool"),
                            }
                        )
                        self._active_step_id = None
                    break

        step: dict[str, Any] | None = None
        if tool_name:
            step = self._find_step_for_tool(tool_name, include_awaiting_hitl=True)
        if step is None and self._active_step_id:
            for candidate in self.steps:
                if str(candidate.get("id")) == self._active_step_id:
                    # interrupt 已声明工具时，不得把其它 running 步（如 get_device_detail）标 awaiting_hitl
                    if not tool_name or candidate.get("tool") == tool_name:
                        step = candidate
                    break
        if step is None and tool_name:
            next_id = str(len(self.steps) + 1)
            step = {
                "id": next_id,
                "label": _tool_step_label(tool_name),
                "tool": tool_name,
                "status": "running",
            }
            self.steps.append(step)
        if step is None:
            return updates
        if step.get("status") not in ("running", "error", "pending"):
            return updates
        step["status"] = "awaiting_hitl"
        self._active_step_id = str(step["id"])
        updates.append(
            {
                "step_id": str(step["id"]),
                "status": "awaiting_hitl",
                "tool": step.get("tool") or tool_name,
            }
        )
        return updates

    def try_replan(
        self,
        *,
        failed_tool: str,
        error_summary: str,
        user_message: str,
    ) -> dict[str, Any] | None:
        """
        失败后生成 Re-plan（每轮最多 MAX_REPLAN_ATTEMPTS 次）。

        参数:
            failed_tool: 失败工具名
            error_summary: 错误摘要
            user_message: 用户原话

        返回:
            replan SSE payload；不可 Re-plan 时返回 None
        """
        if not self.has_plan or self.replan_count >= MAX_REPLAN_ATTEMPTS:
            return None
        new_steps, reason = build_replan_after_failure(
            original_steps=self.steps,
            failed_tool=failed_tool,
            error_summary=error_summary,
            user_message=user_message,
            failed_args=self._last_tool_args.get(failed_tool),
        )
        self.replace_steps(new_steps)
        self.replan_count += 1
        self.last_replan_reason = reason
        return {
            "reason": reason,
            "steps": new_steps,
            "attempt": self.replan_count,
            "failed_tool": failed_tool,
        }


def _write_audit(
    *,
    thread_id: str,
    run_id: str,
    user_id: str,
    event_type: str,
    tool_name: str | None = None,
    payload_summary: dict[str, Any] | None = None,
) -> None:
    """
    写入单条审计记录，失败不影响主流程（静默 catch）。

    参数:
        thread_id, run_id, user_id: 会话标识
        event_type: 审计事件类型
        tool_name: 可选工具名
        payload_summary: 脱敏后的 payload 摘要
    """
    try:
        audit_store.append(
            thread_id=thread_id,
            run_id=run_id,
            user_id=user_id,
            event_type=event_type,
            tool_name=tool_name,
            payload_summary=payload_summary,
        )
    except Exception:
        pass


def _tool_sse_suppressed(tool: str) -> bool:
    """本轮 chat 标记为 stale 的工具（不向 SSE / Plan 透传）。"""
    from platform_mcp.runtime.context import current_turn_suppressed_tools

    return tool in (current_turn_suppressed_tools.get() or frozenset())


async def wrap_stream_with_plan_trace(
    inner: AsyncIterator[tuple[str, dict[str, Any]]],
    *,
    thread_id: str,
    run_id: str,
    user_id: str,
    user_message: str,
    plan_steps: list[dict[str, Any]] | None = None,
    plan_graph: dict[str, Any] | None = None,
    plan_flow_document: dict[str, Any] | None = None,
    auto_replan: bool = True,
) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    """
    包装任意 SSE 事件流，注入 Plan / Trace / Audit。

    参数:
        inner: 内层异步迭代器，产出 (event_name, payload)
        thread_id: 会话 ID
        run_id: 本轮运行 UUID
        user_id: 用户 ID（审计用）
        user_message: 用户原话
        plan_steps: 可选预生成计划；None 则完全动态
        plan_graph / plan_flow_document: BPMN/流程图附加数据
        auto_replan: True 时 envelope 在工具失败且仍有 pending 步时自动 Re-plan

    产出:
        增强后的 SSE 事件（plan、plan_update、replan、trace + 原事件）；
        `__keepalive__` 原样透传，不记 audit。

    副作用:
        finally 中 `trace_store.save_run`（含 plan_snapshot）；审计失败静默忽略。

    说明:
        auto_replan=False（chat/resume 默认）时 Re-plan 由 Plan 执行路径 emit，
        本函数收到外层 replan 事件时只同步 PlanTracker，避免双重规划。
    """
    collector = TraceCollector(thread_id=thread_id, run_id=run_id)
    collector.record_user_message(user_message)
    tracker = PlanTracker(
        plan_steps,
        graph=plan_graph,
        flow_document=plan_flow_document,
        user_message=user_message,
    )

    # 已有预生成 Plan（如 plan_confirm 批准后）时流首即下发，供 TaskProgress 立即展示
    if tracker.has_plan:
        from platform_mcp.runtime.agent_debug import agent_debug, summarize_plan_steps

        agent_debug(
            "flow.plan.tracker_initial",
            thread_id=thread_id,
            plan_steps=summarize_plan_steps(tracker.steps),
        )
        collector.record_plan(tracker.steps, graph=tracker.graph)
        yield ("plan", tracker.initial_payload())
        yield ("trace", collector.events[-1])

    try:
        async for event_name, payload in inner:
            if event_name == "__keepalive__":
                yield ("__keepalive__", {})
                continue

            suppressed_tool = ""
            if event_name in ("tool_start", "tool_end") and isinstance(payload, dict):
                suppressed_tool = str(payload.get("tool", ""))
                if suppressed_tool and _tool_sse_suppressed(suppressed_tool):
                    from platform_mcp.runtime.agent_debug import agent_debug

                    agent_debug(
                        "flow.sse.suppress_stale_tool",
                        thread_id=thread_id,
                        tool=suppressed_tool,
                        sse_event=event_name,
                    )
                    continue

            if event_name == "plan_update":
                if isinstance(payload, dict):
                    tracker.apply_external_plan_update(payload)
                    yield ("plan_update", payload)
                continue

            if event_name == "tool_start":
                tool = str(payload.get("tool", ""))
                tool_args = payload.get("args") if isinstance(payload.get("args"), dict) else None
                had_plan = tracker.has_plan
                plan_update = tracker.on_tool_start(tool, tool_args)
                # 动态 Plan：首次 tool_start 后才 has_plan
                if not had_plan and tracker.has_plan:
                    collector.record_plan(tracker.steps, graph=tracker.graph)
                    yield ("plan", tracker.initial_payload())
                    yield ("trace", collector.events[-1])
                if plan_update:
                    yield ("plan_update", plan_update)

            if event_name == "tool_end":
                tool = str(payload.get("tool", ""))
                ok, summary, stop_retry, user_cancelled = parse_tool_result(
                    str(payload.get("result", ""))
                )
                # 仅用户主动取消标 skipped；non_retryable 硬失败必须标 error
                plan_update = tracker.on_tool_end(tool, ok=ok, user_cancelled=user_cancelled)
                if plan_update:
                    yield ("plan_update", plan_update)

                # 用户取消 / 不可重试硬失败：不 Re-plan
                if user_cancelled or stop_retry:
                    pass
                # 失败且仍有后续 pending 步：跳过后续 + Re-plan
                elif (
                    auto_replan
                    and not ok
                    and tracker.has_plan
                    and any(s.get("status") == "pending" for s in tracker.steps)
                ):
                    for skip_upd in tracker.skip_pending_steps():
                        yield ("plan_update", skip_upd)
                    replan = tracker.try_replan(
                        failed_tool=tool,
                        error_summary=summary,
                        user_message=user_message,
                    )
                    if replan:
                        collector.add(
                            "replan",
                            replan.get("reason", "重新规划"),
                            detail=replan,
                        )
                        _write_audit(
                            thread_id=thread_id,
                            run_id=run_id,
                            user_id=user_id,
                            event_type="replan",
                            tool_name=tool,
                            payload_summary=replan,
                        )
                        yield ("replan", replan)
                        yield ("trace", collector.events[-1])

            if event_name == "interrupt":
                # plan_confirm 时步骤保持 pending，等待用户批准后再执行
                if payload.get("type") != "plan_confirm":
                    tool = str(payload.get("tool", "")) or None
                    for plan_update in tracker.on_interrupt(tool):
                        yield ("plan_update", plan_update)

            if event_name == "replan":
                # Plan 执行路径已 emit replan 时，同步 tracker 状态
                steps = payload.get("steps")
                if isinstance(steps, list):
                    tracker.replace_steps(steps)
                    tracker.replan_count = int(payload.get("attempt") or 1)
                evt = collector.add(
                    "replan",
                    str(payload.get("reason") or "重新规划"),
                    detail=payload if isinstance(payload, dict) else {},
                )
                _write_audit(
                    thread_id=thread_id,
                    run_id=run_id,
                    user_id=user_id,
                    event_type="replan",
                    tool_name=str(payload.get("failed_tool") or "") or None,
                    payload_summary=payload if isinstance(payload, dict) else {},
                )
                yield ("trace", evt)
                yield (event_name, payload)
                continue  # 跳过后方重复 yield

            trace_evt = collector.record_sse(event_name, payload)
            if trace_evt:
                audit_fields = build_audit_from_sse(event_name, payload)
                if audit_fields:
                    evt_type, tool_name, summary = audit_fields
                    _write_audit(
                        thread_id=thread_id,
                        run_id=run_id,
                        user_id=user_id,
                        event_type=evt_type,
                        tool_name=tool_name,
                        payload_summary=summary,
                    )
                yield ("trace", trace_evt)

            yield (event_name, payload)
    finally:
        # 无论正常结束还是异常，都尝试持久化 trace（含 plan 快照供历史恢复）
        try:
            exported = collector.export()
            if tracker.has_plan:
                exported["plan_snapshot"] = tracker.initial_payload()
            trace_store.save_run(exported)
        except Exception:
            pass
