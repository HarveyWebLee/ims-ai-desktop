"""执行循环共享状态与事件转换。"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# LLM 单轮最多工具步数，防止模型死循环连续 tool call。
MAX_EXECUTE_STEPS = 20


@dataclass
class ExecuteState:
    """执行循环运行时状态。"""

    tool_step_count: int = 0
    saw_tool_end: bool = False
    interrupted: bool = False
    last_tool_ok: bool = True
    plan_steps: list[dict[str, Any]] = field(default_factory=list)

    def record_tool_end(self, *, ok: bool) -> None:
        """记录一次 tool_end 观测结果。"""
        self.saw_tool_end = True
        self.tool_step_count += 1
        self.last_tool_ok = ok


def emit_tool_events(
    tool_name: str,
    tool_input: dict[str, Any],
    result: str,
    *,
    retry: bool = False,
    attempt: int = 0,
) -> list[tuple[str, dict[str, Any]]]:
    """构造 tool_start / tool_end SSE 事件对。"""
    start_payload: dict[str, Any] = {"tool": tool_name, "args": tool_input or {}}
    end_payload: dict[str, Any] = {"tool": tool_name, "result": result}
    if retry:
        start_payload["retry"] = True
        start_payload["attempt"] = attempt
        end_payload["retry"] = True
        end_payload["attempt"] = attempt
    return [("tool_start", start_payload), ("tool_end", end_payload)]


def is_task_complete(
    state: ExecuteState,
    *,
    llm_idle: bool = False,
    pending_tool_calls: bool = False,
) -> bool:
    """根据中断、Plan 状态、LLM 空闲与工具步数判断任务是否结束。"""
    if state.interrupted:
        return True

    if state.plan_steps:
        terminal = {"done", "skipped", "error"}
        statuses = [str(step.get("status") or "") for step in state.plan_steps]
        if statuses and all(status in terminal for status in statuses):
            return True
        active = {"pending", "running", "awaiting_confirm", "awaiting_hitl"}
        if any(status in active for status in statuses):
            return False

    if pending_tool_calls:
        return False
    if llm_idle:
        return True
    if state.tool_step_count >= MAX_EXECUTE_STEPS:
        logger.warning("Plan 执行达步数上限: count=%s", state.tool_step_count)
        return True
    return False


def _tool_output_to_str(output: Any) -> str:
    """将 ToolCallStream.output / ToolMessage.content 规范为字符串。"""
    from langchain_core.messages import ToolMessage

    if output is None:
        return ""
    if isinstance(output, str):
        return output
    if isinstance(output, ToolMessage):
        content = output.content
        if isinstance(content, str):
            return content
        if content is not None:
            return json.dumps(content, ensure_ascii=False)
    if isinstance(output, dict):
        content = output.get("content")
        if isinstance(content, str):
            return content
    try:
        return json.dumps(output, ensure_ascii=False)
    except TypeError, ValueError:
        return str(output)
