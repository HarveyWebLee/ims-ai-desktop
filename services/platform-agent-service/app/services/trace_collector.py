"""
执行 Trace 采集服务（Phase 3）：记录每轮对话的工具/计划/中断事件。

文件职责
--------
在一次「用户发消息 → Agent 跑完」的过程中，把发生过的关键事件记成时间线，
结束时打成一包交给 trace_store，供 Trace 面板回放。

一次 run 的链路（白话）
----------------------
把一轮对话想成拍一张「纪实短片」：

  1. stream_chat / resume 开始 → new TraceCollector(thread_id)（开拍）
  2. wrap_stream_with_plan_trace 透传 SSE 时 → record_user_message / record_plan / record_sse
     （镜头：用户原话 → 计划 → tool_start → tool_end → interrupt → replan → done…）
  3. 流结束 finally → collector.export() → trace_store.save_run（存档）
  4. GET trace API → enrich_trace_run → 前端画时间线 / Mermaid 图

同一 thread 可以有很多 run_id（每发一句话通常一场新 run）。

在 Agent 流程中的位置
--------------------
SSE 信封层旁路采集（不改变业务事件，只旁听）：
  stream 事件 → TraceCollector.record_* → 内存 events[] → export

如何被调用
----------
- ``stream_envelope.wrap_stream_with_plan_trace``：边推 SSE 边 record
- 结束处：``trace_store.save_run(collector.export())``

与 audit_store 的区别
--------------------
- TraceCollector：开发者调试视角，完整事件时间线
- audit_store：业务审计，含 user_id、更严格脱敏
"""

from __future__ import annotations

# ── 标准库 ──
import time
import uuid
from typing import Any


def _now_ms() -> int:
    """返回当前 Unix 时间戳（毫秒整数）。"""
    return int(time.time() * 1000)


def _mask_args(args: dict[str, Any] | None) -> dict[str, Any]:
    """
    敏感字段脱敏后供 trace 展示。

    参数:
        args: 工具参数字典

    返回:
        脱敏后的副本
    """
    if not args:
        return {}
    masked: dict[str, Any] = {}
    for key, value in args.items():
        lower = key.lower()
        if any(s in lower for s in ("password", "token", "secret", "authorization")):
            masked[key] = "***"
        else:
            masked[key] = value
    return masked


class TraceCollector:
    """
    单轮对话（run）的 trace 事件缓冲器。

    属性:
        thread_id: 会话线程 ID（哪扇聊天窗）
        run_id: 本轮运行 UUID（哪一场短片；未传入则自动生成）
        events: 已记录的事件列表（按 append 顺序即时间线）
        started_at: 开拍时间（毫秒时间戳）

    典型事件 kind:
        user_message / plan / tool_start / tool_end / interrupt /
        client_action / replan / error / done
    """

    def __init__(self, *, thread_id: str, run_id: str | None = None) -> None:
        self.thread_id = thread_id
        self.run_id = run_id or str(uuid.uuid4())
        self.events: list[dict[str, Any]] = []
        self.started_at = _now_ms()

    def add(
        self,
        kind: str,
        label: str,
        *,
        detail: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        追加一条通用 trace 事件。

        参数:
            kind: 事件类型，如 "tool_start"、"plan"
            label: 人类可读标签
            detail: 可选详情 dict

        返回:
            刚创建的事件 dict（含 id、ts、kind、label、detail）
        """
        event = {
            "id": str(uuid.uuid4()),
            "ts": _now_ms(),
            "kind": kind,
            "label": label,
            "detail": detail or {},
        }
        self.events.append(event)
        return event

    def record_user_message(self, message: str) -> dict[str, Any]:
        """
        记录用户输入（截断预览，避免 trace 过大）。

        参数:
            message: 用户完整输入

        返回:
            trace 事件 dict
        """
        preview = message[:120] + ("…" if len(message) > 120 else "")
        return self.add("user_message", "用户输入", detail={"message": preview})

    def record_plan(
        self, steps: list[dict[str, Any]], *, graph: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        记录任务计划步骤（含可选 graph）。
        """
        detail: dict[str, Any] = {"steps": steps}
        if isinstance(graph, dict):
            detail["graph"] = graph
        return self.add(
            "plan",
            f"任务计划（{len(steps)} 步）",
            detail=detail,
        )

    def record_sse(self, event_name: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        """
        将 SSE 事件名映射为 trace 条目（旁听 stdout，不改写 payload）。

        参数:
            event_name: SSE 事件名（tool_start、interrupt 等）
            payload: 事件 payload

        返回:
            trace 事件 dict；未关心的事件（如纯 token 流）返回 None，避免 trace 爆量
        """
        if event_name == "tool_start":
            tool = str(payload.get("tool", ""))
            return self.add(
                "tool_start",
                f"工具开始：{tool}",
                detail={"tool": tool, "args": _mask_args(payload.get("args"))},
            )
        if event_name == "tool_end":
            from app.services.task_planner import parse_tool_result_ok

            tool = str(payload.get("tool", ""))
            result = str(payload.get("result", ""))
            ok, summary = parse_tool_result_ok(result)
            label = f"工具完成：{tool}" if ok else f"工具失败：{tool}"
            return self.add(
                "tool_end",
                label,
                detail={
                    "tool": tool,
                    "ok": ok,
                    "summary_preview": (summary or "")[:120],
                    "result_preview": result[:200],
                },
            )
        if event_name == "interrupt":
            return self.add(
                "interrupt",
                "等待用户确认/补参",
                detail={"payload": payload},
            )
        if event_name == "client_action":
            action = payload.get("action", "unknown")
            return self.add(
                "client_action",
                f"客户端动作：{action}",
                detail={"action": payload},
            )
        if event_name == "error":
            return self.add(
                "error",
                str(payload.get("message", "执行错误")),
                detail=payload,
            )
        if event_name == "replan":
            return self.add(
                "replan",
                str(payload.get("reason") or "重新规划"),
                detail=payload if isinstance(payload, dict) else {},
            )
        if event_name == "done":
            return self.add("done", "本轮对话结束", detail=payload)
        return None

    def export(self) -> dict[str, Any]:
        """
        导出完整 trace 结构供 trace_store 持久化。

        返回:
            {thread_id, run_id, started_at, ended_at, events}
        """
        return {
            "thread_id": self.thread_id,
            "run_id": self.run_id,
            "started_at": self.started_at,
            "ended_at": _now_ms(),
            "events": self.events,
        }
