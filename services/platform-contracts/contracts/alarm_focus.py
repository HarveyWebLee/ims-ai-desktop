"""
会话告警焦点：从工具结果推断「本轮可回指的告警查询上下文」。

- 唯一告警（详情 / 列表仅 1 条）→ 可回填 alarm_id
- 列表多条 → 不点名，但保留 queryContext（时间/状态/设备）供导出、批量、再查空槽回填
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

_ALARM_TOOLS = frozenset(
    {
        "query_alarms",
        "get_alarm_detail",
        "batch_confirm_alarms",
        "batch_process_alarms",
        "download_file",
    }
)

_ALARM_API_UNPROCESSED = "getAlarmUnprocessList"


@dataclass(frozen=True)
class AlarmFocus:
    """最近一次告警相关工具留下的焦点。"""

    start_time: str = ""
    end_time: str = ""
    status: str = ""
    device_code: str = ""
    device_name: str = ""
    alarm_id: str = ""
    alarm_category_id: list[str] = field(default_factory=list)
    alarm_rank_id: list[str] = field(default_factory=list)
    total: int = 0
    source_tool: str = ""
    hint_message: str = ""

    @property
    def is_unique_alarm(self) -> bool:
        return bool(self.alarm_id.strip()) and (self.total <= 1 or self.total == 0)

    @property
    def has_query_filters(self) -> bool:
        return bool(
            self.start_time.strip()
            or self.end_time.strip()
            or self.status.strip()
            or self.device_code.strip()
            or self.device_name.strip()
            or self.alarm_category_id
            or self.alarm_rank_id
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


def _as_str_list(value: Any) -> list[str]:
    if value is None or value == "" or value == []:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    text = str(value).strip()
    if not text:
        return []
    if "," in text:
        return [p.strip() for p in text.split(",") if p.strip()]
    return [text]


def _status_token_from_query_context(query_context: dict[str, Any]) -> str:
    list_api = str(query_context.get("listApi") or "").strip()
    if list_api == _ALARM_API_UNPROCESSED or "Unprocess" in list_api:
        return "unprocessed"
    codes = _as_str_list(query_context.get("status"))
    if not codes:
        return ""
    if set(codes) == {"1", "2"}:
        return "unprocessed"
    return ",".join(codes) if len(codes) > 1 else codes[0]


def _filters_from_query_context(query_context: Any) -> dict[str, Any]:
    if not isinstance(query_context, dict):
        return {}
    device_codes = _as_str_list(query_context.get("deviceCodes"))
    out: dict[str, Any] = {
        "start_time": str(query_context.get("startTime") or "").strip(),
        "end_time": str(query_context.get("endTime") or "").strip(),
        "status": _status_token_from_query_context(query_context),
        "device_code": device_codes[0] if len(device_codes) == 1 else "",
        "alarm_category_id": _as_str_list(query_context.get("alarmCategoryId")),
        "alarm_rank_id": _as_str_list(query_context.get("alarmRankId")),
    }
    return out


def _alarm_id_from_item(item: dict[str, Any]) -> str:
    return str(item.get("id") or item.get("alarmId") or "").strip()


def alarm_focus_from_tool_result(
    *,
    tool_name: str,
    payload: dict[str, Any],
) -> AlarmFocus | None:
    """从单次 ToolResult JSON 构造告警焦点；非告警工具或失败返回 None。"""
    name = (tool_name or "").strip()
    if name not in _ALARM_TOOLS:
        return None
    if payload.get("ok") is False:
        return None

    data = payload.get("data")
    data_dict: dict[str, Any] = data if isinstance(data, dict) else {}

    if name == "get_alarm_detail":
        aid = _alarm_id_from_item(data_dict)
        if not aid:
            action = payload.get("client_action")
            if isinstance(action, dict):
                raw_params = action.get("params")
                params: dict[str, Any] = raw_params if isinstance(raw_params, dict) else {}
                aid = str(params.get("alarmId") or "").strip()
        if not aid:
            return None
        return AlarmFocus(
            alarm_id=aid,
            total=1,
            source_tool=name,
            device_code=str(data_dict.get("deviceCode") or "").strip(),
            device_name=str(data_dict.get("deviceName") or "").strip(),
            hint_message=f"沿用上一轮告警详情「{aid}」。",
        )

    if name == "query_alarms":
        total = int(data_dict.get("total") or 0)
        raw_items = data_dict.get("items")
        items: list[Any] = raw_items if isinstance(raw_items, list) else []
        item_count = len(items)
        filters = _filters_from_query_context(data_dict.get("queryContext"))
        unique_id = ""
        if total == 1 and items and isinstance(items[0], dict):
            unique_id = _alarm_id_from_item(items[0])
        hint = (
            f"上一轮查询仅命中 1 条告警「{unique_id}」，已自动带入。"
            if unique_id
            else (
                f"上一轮已查询到 {total or item_count} 条告警，"
                "后续导出/批量/再查将沿用其时间与筛选条件。"
            )
        )
        return AlarmFocus(
            start_time=str(filters.get("start_time") or ""),
            end_time=str(filters.get("end_time") or ""),
            status=str(filters.get("status") or ""),
            device_code=str(filters.get("device_code") or ""),
            alarm_id=unique_id,
            alarm_category_id=list(filters.get("alarm_category_id") or []),
            alarm_rank_id=list(filters.get("alarm_rank_id") or []),
            total=total or item_count,
            source_tool=name,
            hint_message=hint,
        )

    # download / batch：优先从 data.queryContext 取筛选；否则仅标记来源
    filters = _filters_from_query_context(data_dict.get("queryContext"))
    if any(filters.values()):
        return AlarmFocus(
            start_time=str(filters.get("start_time") or ""),
            end_time=str(filters.get("end_time") or ""),
            status=str(filters.get("status") or ""),
            device_code=str(filters.get("device_code") or ""),
            alarm_category_id=list(filters.get("alarm_category_id") or []),
            alarm_rank_id=list(filters.get("alarm_rank_id") or []),
            total=int(data_dict.get("total") or data_dict.get("confirmed_count") or 0),
            source_tool=name,
            hint_message="沿用上一轮告警操作的时间与筛选条件。",
        )

    # 无 queryContext 的成功导出/批量：仍标记告警域，供「导出」resource 消歧
    if name in {"download_file", "batch_confirm_alarms", "batch_process_alarms"}:
        return AlarmFocus(
            source_tool=name,
            hint_message="上一轮为告警相关操作。",
        )
    return None


def extract_alarm_focus_from_messages(messages: list[Any]) -> AlarmFocus | None:
    """从近到远扫描 checkpoint messages，取最近一次告警工具焦点。"""
    for msg in reversed(messages or []):
        if not _is_tool_message(msg):
            continue
        tool_name = str(getattr(msg, "name", None) or "").strip()
        payload = _parse_tool_payload(getattr(msg, "content", None))
        if not payload:
            continue
        focus = alarm_focus_from_tool_result(tool_name=tool_name, payload=payload)
        if focus is not None:
            return focus
    return None
