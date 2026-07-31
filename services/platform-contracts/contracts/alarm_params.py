"""告警查询/导出共用的时间与筛选纯函数（供 preflight / plan_confirm / tools 引用）。"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from contracts.time_range import resolve_alarm_time_range

# query_alarms / download_file 缺参时，HITL 表单字段定义（前端据此渲染）
QUERY_ALARM_FIELDS: list[dict[str, Any]] = [
    {
        "name": "time_range",
        "label": "时间范围",
        "type": "datetime_range",
        "required": True,
        "description": "选择开始与结束的日期时间（精确到秒）",
    },
    {
        "name": "alarm_category_id",
        "label": "报警类型",
        "type": "async_select",
        "asyncSource": "alarm_category",
        "required": False,
        "description": "可选，按报警类型筛选",
        "mode": "multiple",
    },
    {
        "name": "alarm_rank_id",
        "label": "报警级别",
        "type": "async_select",
        "asyncSource": "alarm_rank",
        "required": False,
        "description": "可选，按报警级别筛选",
        "mode": "multiple",
    },
    {
        "name": "status",
        "label": "告警状态",
        "type": "select",
        "required": False,
        "description": "可选，按告警状态筛选",
        "mode": "multiple",
        "options": [
            {"label": "未处理（待确认+已确认）", "value": "unprocessed"},
            {"label": "待确认", "value": "1"},
            {"label": "已确认", "value": "2"},
            {"label": "已处理", "value": "3"},
        ],
    },
    {
        "name": "device_code",
        "label": "设备编码",
        "type": "text",
        "required": False,
        "description": "可选，按设备编码筛选（与设备名称二选一）",
    },
    {
        "name": "device_name",
        "label": "设备名称",
        "type": "text",
        "required": False,
        "description": "可选，按设备名称筛选（与设备编码二选一，模糊匹配）",
    },
]

_UNPROCESSED_STATUS_ALIASES = frozenset(
    {"未处理", "未处理告警", "unprocessed", "unprocessed_alarm"}
)
_STATUS_SCOPE_UNPROCESSED = "unprocessed"

_ALARM_STATUS_TOKEN_MAP: dict[str, str] = {
    "未确认": "1",
    "待确认": "1",
    "pending": "1",
    "pending_confirm": "1",
    "已确认": "2",
    "confirmed": "2",
    "已处理": "3",
    "processed": "3",
    "1": "1",
    "2": "2",
    "3": "3",
}


def to_platform_time(value: str) -> str:
    """
    将 ISO8601 或常见 datetime 字符串转为平台要求的格式：YYYY-MM-DD HH:mm:ss。

    平台接口不接受带 T/Z 的 ISO 格式，需统一转换。
    """
    value = value.strip()
    if "T" in value:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    if re.search(r"\d{4}-\d{2}-\d{2}\s+\d{1,2}:\d{2}", value):
        try:
            dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            try:
                dt = datetime.strptime(value, "%Y-%m-%d %H:%M")
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                pass
    return value


def resolve_or_prepare_alarm_times(
    start_time: str,
    end_time: str,
) -> tuple[str, str, bool]:
    """
    解析告警查询/导出所需的时间范围。

    返回三元组 (start_iso, end_iso, needs_hitl)：
        - needs_hitl=False：已成功解析 start/end
        - needs_hitl=True：未提供时间或无法解析，需 HITL 表单由使用者补选
    """
    resolved = resolve_alarm_time_range(start_time, end_time)
    if resolved:
        return resolved[0], resolved[1], False

    has_any = bool(str(start_time or "").strip() or str(end_time or "").strip())
    if not has_any:
        return "", "", True

    return str(start_time or ""), str(end_time or ""), True


def _normalize_hitl_id_list(value: Any) -> list[str]:
    """HITL 多选 / 逗号分隔字符串 → 非空 id 列表。"""
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


def _is_unprocessed_scope_token(token: str) -> bool:
    raw = str(token or "").strip()
    return raw in _UNPROCESSED_STATUS_ALIASES or raw == _STATUS_SCOPE_UNPROCESSED


def _map_alarm_status_token(token: str) -> str:
    raw = str(token or "").strip()
    if not raw:
        return ""
    if raw in _ALARM_STATUS_TOKEN_MAP:
        return _ALARM_STATUS_TOKEN_MAP[raw]
    if raw.isdigit():
        return raw
    return ""


def _normalize_hitl_status_list(value: Any, *, fallback: str = "") -> list[str]:
    items = _normalize_hitl_id_list(value)
    mapped = [_map_alarm_status_token(x) for x in items if not _is_unprocessed_scope_token(x)]
    mapped = [x for x in mapped if x]
    if mapped:
        return mapped
    fb = _map_alarm_status_token(str(fallback or ""))
    return [fb] if fb else []


def _apply_alarm_filter_fields(
    payload: dict[str, Any],
    params: dict[str, Any],
    *,
    status_fallback: str = "",
    alarm_level: str = "",
) -> None:
    """将 HITL/工具参数字典中的筛选条件写入 getAlarmList / export 请求体。"""
    category_ids = _normalize_hitl_id_list(params.get("alarm_category_id"))
    if category_ids:
        payload["alarmCategoryId"] = category_ids

    rank_ids = _normalize_hitl_id_list(params.get("alarm_rank_id") or alarm_level)
    if rank_ids:
        payload["alarmRankId"] = rank_ids

    device_codes = _normalize_hitl_id_list(
        params.get("deviceCodes")
        if params.get("deviceCodes") not in (None, "", [])
        else params.get("device_codes")
        if params.get("device_codes") not in (None, "", [])
        else params.get("device_code")
    )
    if device_codes:
        payload["deviceCodes"] = device_codes

    payload["status"] = _normalize_hitl_status_list(
        params.get("status"),
        fallback=status_fallback,
    )


def build_alarm_list_filter_payload(
    *,
    start_time: str,
    end_time: str,
    filter_params: dict[str, Any] | None = None,
    status_fallback: str = "",
    alarm_level: str = "",
    page: int = 1,
    size: int = 20,
) -> dict[str, Any]:
    """
    构造 getAlarmList / exportAlarm 共用的筛选请求体（不含 ids）。

    供 query_alarms、导出前计数、分批导出复用，保证筛选条件一致。
    """
    params = filter_params or {}
    payload: dict[str, Any] = {
        "startTime": to_platform_time(start_time),
        "endTime": to_platform_time(end_time),
        "page": page,
        "size": size,
        "deviceCodes": [],
        "variableNames": [],
        "alarmCategoryId": [],
        "alarmRankId": [],
        "status": [],
    }
    _apply_alarm_filter_fields(
        payload,
        params,
        status_fallback=status_fallback,
        alarm_level=alarm_level,
    )
    return payload
