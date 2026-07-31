"""
Agent 跨轮次 / 全流程 / AI 介入点排查日志

文件职责
--------
在 ``AGENT_DEBUG_TRACE=true`` 时输出带统一前缀 ``[AgentTrace]`` 的结构化日志，
用于定位 HITL / Plan 污染、错工具、跨轮残留等问题。不改变业务逻辑。

白话概念
--------
侧栏「卡住了 / 又弹出上一轮导出」时，在终端 ``grep AgentTrace``，
看本轮走了哪条路径、BPMN 快照还在不在、SSE 发了啥。

在 Agent 流程中的位置
--------------------
  chat / resume / plan / tool / SSE 关键节点
    → agent_debug("flow.xxx", ...)
  可选：trace_sse_outgoing、orchestration_snapshot

启用方式
--------
- ``uv run dev`` 默认 setdefault 为 true（见 app/dev.py）
- 或 .env：``AGENT_DEBUG_TRACE=true``
- false 时 agent_debug 直接 return，几乎零开销

事件命名约定
------------
    flow.api.*          API 入口
    flow.context.*      上下文组装
    flow.route.*        意图路由
    flow.plan.*         Plan 决策与门控
    flow.ai.*           LLM / 工具调用 / HITL
    flow.checkpoint.*   LangGraph checkpoint 快照
    flow.sse.*          下发前 SSE 摘要（text 仅记长度）
    resume.* / chat.*   编排层
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

# 长文本字段使用更大截断上限（便于分析 AI 输入输出）
_LONG_FIELD_KEYS = frozenset(
    {
        "llm_user_message",
        "user_message",
        "user_prompt",
        "system_preview",
        "content_preview",
        "tool_args",
        "tool_result",
        "result_summary",
        "plan_steps",
        "raw_plan",
        "rule_plan",
        "params_by_tool",
        "interrupt_payload",
        "resume_payload",
        "checkpoint_messages",
        "messages",
        "recent_user_messages",
        "llm_plan_steps",
        "llm_plan_params",
        "preflight_args",
        "metadata",
        "detail",
        "error",
    }
)
_DEFAULT_MAX_LEN = 200
_LONG_MAX_LEN = 800


def _trace_logger() -> logging.Logger:
    """排查日志专用 logger，复用 uvicorn.error 或 stderr。"""
    log = logging.getLogger("app.agent_debug")
    if not log.handlers:
        uvicorn_log = logging.getLogger("uvicorn.error")
        for handler in uvicorn_log.handlers:
            log.addHandler(handler)
        if not log.handlers:
            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(logging.Formatter("%(levelname)s:     %(message)s"))
            log.addHandler(handler)
    log.setLevel(logging.INFO)
    log.propagate = False
    return log


def _is_enabled() -> bool:
    """读取 settings.agent_debug_trace；配置未就绪时视为关闭。"""
    try:
        from platform_mcp.runtime.settings import settings

        return bool(settings.agent_debug_trace)
    except Exception:
        return False


def preview_text(value: Any, *, max_len: int = _LONG_MAX_LEN) -> str:
    """将任意值转为单行可读预览，超长截断并加省略号。"""
    if value is None:
        return "-"
    text = str(value).replace("\r\n", "\n").strip()
    if len(text) > max_len:
        return text[: max_len - 3] + "..."
    return text or "-"


def _fmt(value: Any, *, key: str = "", max_len: int | None = None) -> str:
    """将字段格式化为单行字符串。"""
    if max_len is None:
        max_len = _LONG_MAX_LEN if key in _LONG_FIELD_KEYS else _DEFAULT_MAX_LEN
    if value is None:
        return "-"
    if isinstance(value, str):
        text = value
    elif isinstance(value, (int, float, bool)):
        return str(value)
    else:
        try:
            text = json.dumps(value, ensure_ascii=False, default=str)
        except TypeError, ValueError:
            text = repr(value)
    if len(text) > max_len:
        return text[: max_len - 3] + "..."
    return text


def agent_debug(event: str, *, thread_id: str | None = None, **fields: Any) -> None:
    """
    输出一行结构化排查日志（仅 AGENT_DEBUG_TRACE=true 时生效）。

    参数
    ----
    event : str
        事件名，如 ``flow.plan.gate``、``flow.sse.emit``。
    thread_id : str | None
        会话 ID（会截断展示）；也可放在 fields 里。
    **fields
        任意键值，长字段按 _LONG_FIELD_KEYS 放宽截断上限。
    """
    if not _is_enabled():
        return
    tid = (thread_id or fields.pop("thread_id", None) or "").strip()
    parts = [f"[AgentTrace] {event}"]
    if tid:
        parts.append(f"thread={tid[:12]}")
    for key, value in fields.items():
        parts.append(f"{key}={_fmt(value, key=key)}")
    _trace_logger().info(" | ".join(parts))


def summarize_tool_args(args: dict[str, Any] | None) -> dict[str, Any]:
    """工具参数摘要（用于日志，不含 token）。"""
    if not args:
        return {}
    out: dict[str, Any] = {}
    for key, value in args.items():
        if str(key).startswith("_"):
            continue
        if isinstance(value, str) and len(value) > 120:
            out[key] = value[:117] + "..."
        else:
            out[key] = value
    return out


def summarize_tool_result(result: str | None) -> dict[str, Any]:
    """解析 tool_result JSON 为摘要字段。"""
    if not result:
        return {"empty": True}
    try:
        data = json.loads(result)
        if isinstance(data, dict):
            summary: dict[str, Any] = {
                "ok": data.get("ok"),
                "summary": preview_text(data.get("summary"), max_len=160),
            }
            if data.get("user_cancelled"):
                summary["user_cancelled"] = True
            if data.get("client_action"):
                summary["has_client_action"] = True
            if data.get("client_actions"):
                summary["client_actions_count"] = len(data["client_actions"])
            return summary
    except json.JSONDecodeError, TypeError:
        pass
    return {"raw_preview": preview_text(result, max_len=160)}


def summarize_plan_steps(steps: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    """Plan 步骤摘要。"""
    if not steps:
        return []
    out: list[dict[str, str]] = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        out.append(
            {
                "id": str(step.get("id") or ""),
                "tool": str(step.get("tool") or ""),
                "status": str(step.get("status") or ""),
                "label": preview_text(step.get("label"), max_len=40),
            }
        )
    return out


def trace_sse_outgoing(event_name: str, payload: dict[str, Any] | None) -> None:
    """SSE 下发前摘要（message 类事件仅记录 delta 长度，避免刷屏）。"""
    if not _is_enabled():
        return
    data = payload or {}
    if event_name == "message":
        delta = str(data.get("delta") or "")
        if not delta:
            return
        agent_debug(
            "flow.sse.text_delta",
            chars=len(delta),
            preview=preview_text(delta, max_len=80),
        )
        return
    if event_name in (
        "tool_start",
        "tool_end",
        "interrupt",
        "plan",
        "plan_update",
        "replan",
        "error",
        "done",
    ):
        fields: dict[str, Any] = {"sse_event": event_name}
        if event_name == "tool_start":
            fields["tool"] = data.get("tool")
            fields["tool_args"] = summarize_tool_args(
                data.get("args") if isinstance(data.get("args"), dict) else {}
            )
        elif event_name == "tool_end":
            fields["tool"] = data.get("tool")
            fields["result_summary"] = summarize_tool_result(str(data.get("result") or ""))
        elif event_name == "interrupt":
            fields["interrupt_type"] = data.get("type")
            fields["tool"] = data.get("tool")
            fields["message_preview"] = preview_text(data.get("message"), max_len=120)
        elif event_name == "plan":
            steps = data.get("steps") if isinstance(data.get("steps"), list) else data
            if isinstance(steps, list):
                fields["plan_steps"] = summarize_plan_steps(steps)
        elif event_name == "plan_update":
            fields.update({k: data.get(k) for k in ("step_id", "status", "tool") if k in data})
        elif event_name == "error":
            fields["code"] = data.get("code")
            fields["message"] = preview_text(data.get("message"), max_len=160)
        agent_debug("flow.sse.emit", **fields)


def orchestration_snapshot(thread_id: str) -> dict[str, Any]:
    """编排调试快照：BPMN 快照与 execution_state 是否存在。"""
    tid = (thread_id or "").strip()
    snap: dict[str, Any] = {"thread_id": tid}
    try:
        from app.services.session_store import get_thread_bpmn_snapshot

        bpmn = get_thread_bpmn_snapshot(tid)
        snap["has_bpmn_snapshot"] = bpmn is not None
    except Exception:  # noqa: BLE001
        snap["has_bpmn_snapshot"] = False
    try:
        from app.services.bpmn_execution_state import get_bpmn_execution_state

        snap["has_execution_state"] = get_bpmn_execution_state(tid) is not None
    except Exception:  # noqa: BLE001
        snap["has_execution_state"] = False
    return snap
