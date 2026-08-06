"""
HITL 辅助（Platform MCP 进程）

本进程 **不** 依赖 LangGraph。需人工介入时抛 ``McpHitlSignal``，
由 ``server.py`` 序列化为 ``{ hitl_required, payload }``；
Agent Client 在图内调用 ``interrupt(payload)``，resume 后重调本工具。

跨进程 bypass：``X-Hitl-Confirm-Bypass`` → ``current_hitl_confirm_bypass``，
跳过 ``ask_user_confirm``。
"""

from __future__ import annotations

from typing import Any

from contracts.context import current_hitl_confirm_bypass, current_run_mode


class McpHitlSignal(Exception):
    """
    工具需要人工补参或确认；由 MCP server 层转为 hitl_required JSON。

    属性
    ----
    payload : dict
        与前端 interrupt SSE 相同结构（type/tool/message/fields 等）。
    """

    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        super().__init__(payload.get("message") or "需要人工确认或补参")


def _has_value(value: Any) -> bool:
    """判断参数值是否有效（非空）。"""
    if value is None:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    if isinstance(value, (list, dict)) and not value:
        return False
    return True


def _normalize_hitl_args(data: dict[str, Any]) -> dict[str, Any]:
    """展开 HITL 参数：time_range → start_time / end_time。"""
    out = dict(data)
    for key, value in list(out.items()):
        if isinstance(value, str):
            out[key] = value.strip()
    tr = out.get("time_range")
    if isinstance(tr, dict):
        if tr.get("start_time"):
            out.setdefault("start_time", tr["start_time"])
        if tr.get("end_time"):
            out.setdefault("end_time", tr["end_time"])
        del out["time_range"]
    return out


def _field_has_value(field: dict[str, Any], data: dict[str, Any]) -> bool:
    """按字段类型判断是否已满足必填。"""
    name = field.get("name", "")
    ftype = field.get("type")

    if ftype == "datetime_range":
        tr = data.get(name)
        if isinstance(tr, dict):
            return _has_value(tr.get("start_time")) and _has_value(tr.get("end_time"))
        return _has_value(data.get("start_time")) and _has_value(data.get("end_time"))

    return _has_value(data.get(name))


def ask_user_params(
    *,
    tool: str,
    message: str,
    fields: list[dict[str, Any]],
    current: dict[str, Any],
) -> dict[str, Any]:
    """
    检查必填字段；缺失则抛 ``McpHitlSignal``（由 Agent 图 interrupt 后重调）。

    重调时 ``current`` 已含用户补填值，本函数直接返回合并结果。
    """
    current = _normalize_hitl_args(dict(current))
    missing = [f for f in fields if f.get("required") and not _field_has_value(f, current)]
    if not missing:
        return current

    raise McpHitlSignal(
        {
            "type": "ask_params",
            "tool": tool,
            "message": message,
            "fields": fields,
            "current": current,
        }
    )


def ask_user_confirm(
    *,
    tool: str,
    message: str,
    device_preview: dict[str, Any] | None = None,
) -> bool:
    """
    写操作确认；无 bypass 时抛 ``McpHitlSignal``。

    Agent resume 批准后应带 ``X-Hitl-Confirm-Bypass`` 重调，本函数返回 True。
    ``current_run_mode == autonomous`` 时跳过 confirm（缺参仍走 ask_params）。
    device_preview：可选，send_device_cmd 等指令确认前附带设备摘要（前端同屏展示）。
    """
    if current_hitl_confirm_bypass.get():
        return True
    if current_run_mode.get() == "autonomous":
        return True

    payload: dict[str, Any] = {
        "type": "confirm",
        "tool": tool,
        "message": message,
    }
    if device_preview:
        payload["device_preview"] = device_preview

    raise McpHitlSignal(payload)


def merge_hitl_resume_args(resume_value: Any, tool_args: dict[str, Any]) -> dict[str, Any]:
    """将 resume 表单参数合并进工具参数（Agent 侧续跑用）。"""
    merged = dict(tool_args)
    if not isinstance(resume_value, dict):
        return merged

    resume_type = resume_value.get("type")
    if resume_type in ("approve", "reject"):
        nested = resume_value.get("args")
        if not isinstance(nested, dict):
            return merged
        source = nested
    elif "args" in resume_value and isinstance(resume_value.get("args"), dict):
        source = resume_value["args"]
    else:
        source = resume_value

    args = _normalize_hitl_args(dict(source))
    args = {
        k: v
        for k, v in args.items()
        if not str(k).startswith("_hitl_") and k not in ("type", "approved")
    }
    merged.update({k: v for k, v in args.items() if v is not None and v != ""})
    return _normalize_hitl_args(merged)


def extract_expected_hitl_tool(resume_value: Any) -> str | None:
    """从 resume 载荷读取前端声明的 ``_hitl_tool``。"""
    if not isinstance(resume_value, dict):
        return None
    direct = resume_value.get("_hitl_tool")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()
    args = resume_value.get("args")
    if isinstance(args, dict):
        nested = args.get("_hitl_tool")
        if isinstance(nested, str) and nested.strip():
            return nested.strip()
    return None


def strip_hitl_meta_from_resume(resume_value: Any) -> Any:
    """移除 resume 中 ``_hitl_`` 元字段。"""
    if not isinstance(resume_value, dict):
        return resume_value
    cleaned = {k: v for k, v in resume_value.items() if not str(k).startswith("_hitl_")}
    args = cleaned.get("args")
    if isinstance(args, dict):
        cleaned["args"] = {k: v for k, v in args.items() if not str(k).startswith("_hitl_")}
    return cleaned


def is_hitl_reject(resume_value: Any) -> bool:
    """判断 resume 是否表示拒绝。"""
    if not isinstance(resume_value, dict):
        return False
    if resume_value.get("type") == "reject":
        return True
    if resume_value.get("approved") is False:
        return True
    if resume_value.get("type") == "respond":
        args = resume_value.get("args") or {}
        return isinstance(args, dict) and args.get("approved") is False
    return False


def is_hitl_approve(resume_value: Any) -> bool:
    """判断 resume 是否表示批准。"""
    if not isinstance(resume_value, dict):
        return bool(resume_value)
    if resume_value.get("type") == "reject":
        return False
    if resume_value.get("approved") is False:
        return False
    if resume_value.get("type") == "approve" or resume_value.get("approved") is True:
        return True
    if resume_value.get("type") == "respond":
        args = resume_value.get("args") or {}
        if isinstance(args, dict) and args.get("approved") is False:
            return False
        return True
    return False
