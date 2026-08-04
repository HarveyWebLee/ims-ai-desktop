"""
会话设备焦点：从工具结果 / 用户句推断「本轮可回指的设备上下文」。

- 唯一设备（详情 / 列表仅 1 台 / 刚下发成功）→ 可直接回填 device_code
- 多台列表 → 不自动点名，但保留 queryContext 供 HITL device_picker 预填筛选
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

_DEVICE_TOOLS = frozenset(
    {
        "query_devices",
        "get_device_detail",
        "send_device_cmd",
        "query_device_variables",
        "query_device_variable_realtime",
        "query_device_variable_history",
    }
)


@dataclass(frozen=True)
class DeviceFocus:
    """最近一次设备相关工具留下的焦点。"""

    device_code: str = ""
    device_name: str = ""
    total: int = 0
    source_tool: str = ""
    # 供前端 device_picker 预填：onlineStatus / deviceName / deviceCode / search
    default_filters: dict[str, Any] = field(default_factory=dict)
    hint_message: str = ""

    @property
    def is_unique(self) -> bool:
        return bool((self.device_code or self.device_name).strip()) and (
            self.total <= 1 or bool(self.device_code.strip())
        )


def _parse_tool_payload(content: Any) -> dict[str, Any] | None:
    if isinstance(content, dict):
        return content
    if not isinstance(content, str):
        return None
    text = content.strip()
    if not text.startswith("{"):
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _is_tool_message(msg: Any) -> bool:
    """不依赖 langchain_core：按 type / 类名识别 ToolMessage。"""
    if msg is None:
        return False
    if getattr(msg, "type", None) == "tool":
        return True
    return type(msg).__name__ == "ToolMessage"


def _filters_from_query_context(query_context: Any) -> dict[str, Any]:
    if not isinstance(query_context, dict):
        return {}
    out: dict[str, Any] = {}
    online = query_context.get("onlineStatus")
    if online is not None and str(online).strip() != "":
        try:
            out["onlineStatus"] = int(online)
        except TypeError, ValueError:
            pass
    for src, dst in (
        ("deviceName", "deviceName"),
        ("deviceCode", "deviceCode"),
        ("search", "deviceName"),  # 模糊词落到名称筛选，便于用户接着搜
    ):
        val = str(query_context.get(src) or "").strip()
        if val and dst not in out:
            out[dst] = val
    return out


def device_focus_from_tool_result(
    *,
    tool_name: str,
    payload: dict[str, Any],
) -> DeviceFocus | None:
    """从单次 ToolResult JSON 构造焦点；非设备工具或失败返回 None。"""
    name = (tool_name or "").strip()
    if name not in _DEVICE_TOOLS:
        return None
    if payload.get("ok") is False:
        return None

    data = payload.get("data")
    data_dict: dict[str, Any] = data if isinstance(data, dict) else {}

    if name == "get_device_detail":
        raw_device = data_dict.get("device")
        device: dict[str, Any] = raw_device if isinstance(raw_device, dict) else {}
        code = str(device.get("deviceCode") or "").strip()
        dname = str(device.get("deviceName") or "").strip()
        if not code and not dname:
            return None
        return DeviceFocus(
            device_code=code,
            device_name=dname,
            total=1,
            source_tool=name,
            hint_message=f"沿用上一轮设备详情「{dname or code}」。",
        )

    if name == "query_devices":
        total = int(data_dict.get("total") or 0)
        raw_items = data_dict.get("items")
        items: list[Any] = raw_items if isinstance(raw_items, list) else []
        item_count = len(items)
        filters = _filters_from_query_context(data_dict.get("queryContext"))
        if total == 1 and items:
            first = items[0] if isinstance(items[0], dict) else {}
            code = str(first.get("deviceCode") or "").strip()
            dname = str(first.get("deviceName") or "").strip()
            return DeviceFocus(
                device_code=code,
                device_name=dname,
                total=1,
                source_tool=name,
                default_filters=filters,
                hint_message=f"上一轮查询仅命中 1 台设备「{dname or code}」，已自动带入。",
            )
        # 多台：不点名，但保留筛选（如在线）供 HITL 预填
        scope = "在线" if filters.get("onlineStatus") == 1 else "符合上次条件"
        resolved_total = total or item_count
        return DeviceFocus(
            total=resolved_total,
            source_tool=name,
            default_filters=filters,
            hint_message=(
                f"上一轮已查询到 {resolved_total} 台{scope}设备，"
                "请从中单选要操作的目标设备（已预填上次筛选条件）。"
            ),
        )

    if name == "send_device_cmd":
        code = ""
        dname = ""
        raw_device = data_dict.get("device")
        if isinstance(raw_device, dict):
            code = str(raw_device.get("deviceCode") or "").strip()
            dname = str(raw_device.get("deviceName") or "").strip()
        if not code:
            code = str(data_dict.get("deviceCode") or "").strip()
        if not dname:
            dname = str(data_dict.get("deviceName") or "").strip()
        if not code:
            return None
        return DeviceFocus(
            device_code=code,
            device_name=dname,
            total=1,
            source_tool=name,
            hint_message=f"沿用上一轮已操作设备「{dname or code}」。",
        )

    # 变量类工具：args 常在外层；结果 data 可能含 deviceCode
    code = str(data_dict.get("deviceCode") or "").strip()
    dname = str(data_dict.get("deviceName") or "").strip()
    if code or dname:
        return DeviceFocus(
            device_code=code,
            device_name=dname,
            total=1,
            source_tool=name,
            hint_message=f"沿用上一轮设备「{dname or code}」。",
        )
    return None


def extract_device_focus_from_messages(messages: list[Any]) -> DeviceFocus | None:
    """从近到远扫描 checkpoint messages，取最近一次设备工具焦点。"""
    for msg in reversed(messages or []):
        if not _is_tool_message(msg):
            continue
        tool_name = str(getattr(msg, "name", None) or "").strip()
        payload = _parse_tool_payload(getattr(msg, "content", None))
        if not payload:
            continue
        focus = device_focus_from_tool_result(tool_name=tool_name, payload=payload)
        if focus is not None:
            return focus
    return None


def apply_device_focus_to_interrupt(
    interrupt: dict[str, Any] | None,
    focus: DeviceFocus | None,
) -> dict[str, Any] | None:
    """把多台列表的筛选条件写入 device_picker；有 hint 时改写引导文案。"""
    if not interrupt or not isinstance(interrupt, dict):
        return interrupt
    if not focus:
        return interrupt
    out = dict(interrupt)
    fields = list(out.get("fields") or [])
    changed = False
    new_fields: list[Any] = []
    for raw in fields:
        if not isinstance(raw, dict):
            new_fields.append(raw)
            continue
        field = dict(raw)
        if field.get("type") == "device_picker" and focus.default_filters:
            field["defaultFilters"] = dict(focus.default_filters)
            if focus.hint_message:
                field["description"] = focus.hint_message
            changed = True
        new_fields.append(field)
    if changed:
        out["fields"] = new_fields
    if focus.hint_message and any(
        isinstance(f, dict) and f.get("type") == "device_picker" for f in new_fields
    ):
        # 仅当仍在问设备时覆盖 message
        msg = str(out.get("message") or "")
        if (not msg) or re.search(r"设备|未指定|选择", msg):
            out["message"] = focus.hint_message
    return out
