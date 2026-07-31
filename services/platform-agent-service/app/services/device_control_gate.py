"""
纯设备控制意图的父图门控（classify → device_gate）。

在进入 ReAct / 工具循环前，对设备控制（含通用「下发指令」）且槽位未齐的场景
直接 resolve → ask_params interrupt，避免并行误调工具或模型闲聊收窄能力范围。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.graph.context import AgentContext
from app.services.prompt_assembly import parse_device_control_action

# 供单测与其它模块从本门控入口引用（实现位于 prompt_assembly）
__all__ = (
    "DeviceControlHitlGate",
    "parse_device_control_action",
    "prepare_device_control_hitl_gate",
)

_DEVICE_CONTROL_TOOL = "send_device_cmd"
_DEVICE_CONTROL_CONTINUATION = "device_control_chat"


@dataclass(frozen=True)
class DeviceControlHitlGate:
    """设备控制门控产物：缺槽时的 interrupt 载荷与已知参数。"""

    action: str
    tool_args: dict[str, Any]
    interrupt_payload: dict[str, Any]
    # 续跑提示元数据（非 session pending；父图实际用 interrupt_payload + device_tool_args）
    resume_hint: dict[str, Any]


def prepare_device_control_hitl_gate(
    ctx: AgentContext,
    *,
    model_id: str = "",
) -> DeviceControlHitlGate | None:
    """
    纯设备控制且 resolve 需要 ask_params 时，返回父图 device_gate 载荷。

    - 具体动作（开门/关门/播报）：带 action 消解
    - 通用「下发指令」：action 留空，HITL 选设备 + 变量/写入值
    - 三要素已齐时返回 None，交由 ReAct 正常下发
    """
    from contracts.device_command_resolver import resolve_device_command

    message = (ctx.message or "").strip()
    action = parse_device_control_action(message)
    if action is None:
        return None

    resolution = resolve_device_command(
        action=action,
        user_text=message,
    )
    if resolution.is_complete():
        return None

    interrupt = resolution.interrupt
    if not interrupt or interrupt.get("type") != "ask_params":
        return None

    fields = list(interrupt.get("fields") or [])
    if not fields:
        return None

    tool_args = {**resolution.to_tool_args()}
    if action:
        tool_args["action"] = action
    interrupt_payload = {
        "type": "ask_params",
        "tool": _DEVICE_CONTROL_TOOL,
        "message": str(interrupt.get("message") or "请补充设备指令参数"),
        "fields": fields,
    }
    resume_hint = {
        "continuation": _DEVICE_CONTROL_CONTINUATION,
        "tool": _DEVICE_CONTROL_TOOL,
        "tool_args": tool_args,
        "interrupt_type": "ask_params",
        "user_message": message,
        "model_id": model_id,
    }
    return DeviceControlHitlGate(
        action=action,
        tool_args=tool_args,
        interrupt_payload=interrupt_payload,
        resume_hint=resume_hint,
    )
