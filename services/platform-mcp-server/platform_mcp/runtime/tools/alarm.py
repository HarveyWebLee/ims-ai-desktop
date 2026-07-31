"""
告警相关 Server Tools 模块

文件职责
--------
向 LLM 暴露告警查询 / 详情 / 批量确认 / 批量处理四类工具；
内部经 ``platform_client`` 调用平台 ``/alarm/*``，统一返回 ``tool_result`` JSON。

白话概念
--------
值班员说「查近三天未处理告警」「帮我批量确认」时，LLM 选中本模块工具。
查列表偏只读；确认/处理会改状态，必须先 HITL 点同意。

在 Agent 流程中的位置
--------------------
  LLM / Plan 选中工具
    → ensure_tool_args（缺参 → ask_params HITL，见 tool_preflight）
    → 本模块 @tool
    → call_platform_api → ToolResult（含 data / client_action）
  导出复用：export.py 调用本模块的筛选 / 计数公开 helper

对外工具与平台 API
------------------
| 工具 | 主要平台 API | HITL 何时触发 | ToolResult 要点 |
| ---- | ------------ | ------------- | --------------- |
| query_alarms | POST getAlarmList 或 getAlarmUnprocessList | 时间等缺参走 preflight ask_params | data.total/items/queryContext |
| get_alarm_detail | POST getAlarmList（ids） | 缺 alarm_id → ask_params | data 全量记录 + openModal |
| batch_confirm_alarms | 先列表再 POST confirmAlarm | 写前 ask_user_confirm；拒绝设 user_cancelled | confirmed_count + refresh |
| batch_process_alarms | 先列表再 POST processAlarm | 同上 | processed_count + refresh |

产品语义（status）
------------------
- 1 待确认、2 已确认、3 已处理
- 「未处理」= 1+2，走 getAlarmUnprocessList
- 确认：1→2；处理：1 或 2→3
"""

from __future__ import annotations

import re  # 正则：检测日期时间字符串格式
from datetime import datetime  # 解析与格式化时间
from typing import Any

from langchain_core.tools import tool  # LangChain Tool 装饰器

from platform_mcp.runtime.auth_util import get_username_from_token
from platform_mcp.runtime.context import current_auth_token
from platform_mcp.runtime.hitl import ask_user_confirm  # 人在回路：补参/确认
from platform_mcp.runtime.platform_client import PlatformApiError, call_platform_api
from platform_mcp.runtime.result import tool_result
from platform_mcp.runtime.time_range import resolve_alarm_time_range  # 解析「近三天」等相对时间

# query_alarms 分页大小（平台 getAlarmList；前端 Workspace 翻页复用 queryContext）
QUERY_ALARM_PAGE_SIZE = 20
# 批量确认拉取上限（防止一次确认过多）
BATCH_CONFIRM_FETCH_MAX = 500
BATCH_CONFIRM_PAGE_SIZE = 100

# 产品语义（与 App ALARM_STATUS / DeviceUnhandleAlarm 一致）：
# - status 1=待确认（未确认）、2=已确认、3=已处理
# - 「未处理」= 1+2，不含 3；专用接口 getAlarmUnprocessList
# - 「待确认/未确认」= 仅 status 1
_UNPROCESSED_STATUS_ALIASES = frozenset(
    {"未处理", "未处理告警", "unprocessed", "unprocessed_alarm"}
)
_PENDING_CONFIRM_ALIASES = frozenset({"待确认", "未确认", "pending", "pending_confirm"})
# HITL 下拉：未处理范围专用值（非平台 status 码）
_STATUS_SCOPE_UNPROCESSED = "unprocessed"
_ALARM_API_LIST = "getAlarmList"
_ALARM_API_UNPROCESSED = "getAlarmUnprocessList"

# query_alarms / download_file 缺参时，HITL 表单字段定义（前端据此渲染）
_QUERY_ALARM_FIELDS = [
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

# get_alarm_detail 缺 alarm_id 时的 HITL 表单
_GET_DETAIL_FIELDS = [
    {
        "name": "alarm_id",
        "label": "告警编号",
        "type": "string",
        "required": True,
        "description": "业务系统中的告警 id",
    },
]


# 与前端 AlarmContent / ALARM_STATUS 一致：status 数字码 → 中文标签
_ALARM_STATUS_LABELS: dict[int, str] = {
    1: "待确认",
    2: "已确认",
    3: "已处理",
}

# 口语 / HITL → 平台 status 数字码（1/2/3）；「未处理」见 _parse_alarm_list_scope，不在此映射
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


def _format_alarm_status(item: dict[str, Any]) -> str:
    """
    将平台返回的告警 status 转为可读中文。

    优先使用平台提供的 statusName；否则按数字码查表；无法解析则原样或「未知状态」。
    """
    if item.get("statusName"):
        return str(item["statusName"])
    raw = item.get("status")
    if raw is None or raw == "":
        return "未知状态"
    try:
        code = int(raw)
        return _ALARM_STATUS_LABELS.get(code, str(raw))
    except TypeError, ValueError:
        return str(raw)


def _to_platform_time(value: str) -> str:
    """
    将 ISO8601 或常见 datetime 字符串转为平台要求的格式：YYYY-MM-DD HH:mm:ss。

    平台接口不接受带 T/Z 的 ISO 格式，需统一转换。
    """
    value = value.strip()
    # ISO8601：2024-01-01T12:00:00 或带 Z 时区
    if "T" in value:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    # 已是「YYYY-MM-DD HH:mm:ss」或「YYYY-MM-DD HH:mm」
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
    # 无法识别则原样返回，由平台侧校验
    return value


def _map_alarm_brief_item(item: dict[str, Any]) -> dict[str, Any]:
    """单条告警 → Workspace / LLM 摘要字段。"""
    return {
        "id": item.get("id"),
        "deviceName": item.get("deviceName"),
        "variableName": item.get("variableName"),
        "startTime": item.get("startTime"),
        "status": item.get("status"),
        "statusName": _format_alarm_status(item),
        "alarmRankName": item.get("alarmRankName"),
    }


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
        "startTime": _to_platform_time(start_time),
        "endTime": _to_platform_time(end_time),
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


def resolve_alarm_filter_scope(
    filter_params: dict[str, Any] | None,
    *,
    status_fallback: str = "",
) -> tuple[str, list[str]]:
    """
    解析告警筛选范围（与 query_alarms 一致）。

    返回:
        (list_api, status_codes)
        list_api: getAlarmList | getAlarmUnprocessList
    """
    params = filter_params or {}
    raw_status = params.get("status")
    if raw_status is not None and raw_status != "" and raw_status != []:
        return _parse_hitl_status_scope(raw_status)
    fallback = str(status_fallback or "").strip()
    if fallback:
        return _parse_alarm_list_scope(fallback)
    return _ALARM_API_LIST, []


def export_status_codes_for_scope(list_api: str, status_codes: list[str]) -> list[str]:
    """
    exportAlarm 使用的 status 数组。

    查询「未处理」走 getAlarmUnprocessList，但导出仅有 exportAlarm（基于 getAlarmList），
    未处理全集用 status 1+2 等价筛选。
    """
    if list_api == _ALARM_API_UNPROCESSED:
        return list(status_codes) if status_codes else ["1", "2"]
    return list(status_codes)


def count_alarms_matching_filters(
    *,
    start_time: str,
    end_time: str,
    filter_params: dict[str, Any] | None = None,
    status_fallback: str = "",
    alarm_level: str = "",
) -> int:
    """按与 query_alarms / 导出相同的筛选条件统计告警总数（含未处理专口）。"""
    list_api, status_codes = resolve_alarm_filter_scope(
        filter_params,
        status_fallback=status_fallback,
    )
    _, total = _fetch_alarm_list_paginated(
        start_time=start_time,
        end_time=end_time,
        filter_params=filter_params or {},
        list_api=list_api,
        status_codes=status_codes,
        page_size=1,
        max_records=1,
    )
    return total


def _summarize_alarm_list(
    data: Any,
    *,
    brief_limit: int = 10,
) -> tuple[int, list[dict[str, Any]]]:
    """
    从平台分页响应中提取总条数与精简列表。

    brief_limit：返回给前端的条数上限（query_alarms Workspace 用 PAGE_SIZE；LLM 摘要默认 10）
    """
    if isinstance(data, dict):
        records = data.get("records") or data.get("list") or data.get("rows") or []
        total = data.get("total") or data.get("totalCount") or len(records)
    elif isinstance(data, list):
        records = data
        total = len(records)
    else:
        records = []
        total = 0

    brief = []
    for item in records[:brief_limit]:
        if not isinstance(item, dict):
            continue
        brief.append(_map_alarm_brief_item(item))
    return int(total), brief


def _normalize_hitl_id_list(value: Any) -> list[str]:
    """HITL 多选/单选字段 → 平台 API 所需的字符串 id 列表。"""
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [str(v) for v in value if v not in (None, "")]
    return [str(value)]


def _is_unprocessed_scope_token(token: str) -> bool:
    """是否为「未处理」范围（1+2），而非单一 status 码。"""
    raw = str(token or "").strip()
    return raw in _UNPROCESSED_STATUS_ALIASES or raw == _STATUS_SCOPE_UNPROCESSED


def _parse_alarm_list_scope(status: str) -> tuple[str, list[str]]:
    """
    解析告警列表应走的平台接口与 status 筛选。

    产品定义：
    - 未处理 → getAlarmUnprocessList（待确认+已确认，不含已处理）
    - 待确认/未确认 → getAlarmList + status=[1]
    - 已确认/已处理 → getAlarmList + 对应 status

    返回:
        (list_api, status_codes)
        list_api: _ALARM_API_UNPROCESSED | _ALARM_API_LIST
        status_codes: 传给平台 status 数组；未处理接口默认 [] 表示 1+2
    """
    raw = str(status or "").strip()
    if not raw:
        return _ALARM_API_LIST, []
    if _is_unprocessed_scope_token(raw):
        return _ALARM_API_UNPROCESSED, []
    if raw in _PENDING_CONFIRM_ALIASES:
        return _ALARM_API_LIST, ["1"]
    mapped = _map_alarm_status_token(raw)
    if mapped:
        return _ALARM_API_LIST, [mapped]
    return _ALARM_API_LIST, []


def _parse_hitl_status_scope(value: Any) -> tuple[str, list[str]]:
    """
    从 HITL 多选 / 工具 status 参数解析列表范围。

    多选同时含 unprocessed 与具体码时，以未处理接口为准。
    """
    items = _normalize_hitl_id_list(value)
    if not items:
        return _ALARM_API_LIST, []
    if any(_is_unprocessed_scope_token(x) for x in items):
        # 在未处理范围内可再筛 1/2
        codes = [_map_alarm_status_token(x) for x in items if not _is_unprocessed_scope_token(x)]
        codes = [c for c in codes if c]
        return _ALARM_API_UNPROCESSED, codes
    codes = [_map_alarm_status_token(x) for x in items]
    codes = [c for c in codes if c]
    return _ALARM_API_LIST, codes


def _map_alarm_status_token(token: str) -> str:
    """将中文状态名 / 数字码统一为平台 status 字符串（1/2/3）。"""
    raw = str(token or "").strip()
    if not raw:
        return ""
    if raw in _ALARM_STATUS_TOKEN_MAP:
        return _ALARM_STATUS_TOKEN_MAP[raw]
    if raw.isdigit():
        return raw
    return ""


def _normalize_hitl_status_list(value: Any, *, fallback: str = "") -> list[str]:
    """HITL 告警状态 → 平台 status 数字码列表（不含 unprocessed 范围符）。"""
    items = _normalize_hitl_id_list(value)
    mapped = [_map_alarm_status_token(x) for x in items if not _is_unprocessed_scope_token(x)]
    mapped = [x for x in mapped if x]
    if mapped:
        return mapped
    fb = _map_alarm_status_token(str(fallback or ""))
    return [fb] if fb else []


def build_alarm_unprocess_list_payload(
    *,
    start_time: str,
    end_time: str,
    filter_params: dict[str, Any] | None = None,
    status_codes: list[str] | None = None,
    page: int = 1,
    size: int = 20,
) -> dict[str, Any]:
    """
    构造 getAlarmUnprocessList 请求体（与 DeviceUnhandleAlarm 一致）。

    未传 status_codes 时接口返回「未处理」全集（待确认+已确认）。
    """
    params = filter_params or {}
    payload: dict[str, Any] = {
        "startTime": start_time,
        "endTime": end_time,
        "page": page,
        "size": size,
        "deviceCodes": [],
        "variableNames": [],
        "alarmCategoryId": [],
        "alarmRankId": [],
        "status": [],
    }
    _apply_alarm_filter_fields(payload, params, status_fallback="")
    if status_codes is not None:
        payload["status"] = list(status_codes)
    return payload


def _alarm_api_path(list_api: str) -> str:
    """列表 API 名 → HTTP path。"""
    if list_api == _ALARM_API_UNPROCESSED:
        return "/alarm/getAlarmUnprocessList"
    return "/alarm/getAlarmList"


def _fetch_alarm_list_paginated(
    *,
    start_time: str,
    end_time: str,
    filter_params: dict[str, Any],
    list_api: str,
    status_codes: list[str],
    page_size: int,
    max_records: int,
) -> tuple[list[dict[str, Any]], int]:
    """按范围分页拉取告警列表，返回 (records, total)。"""
    platform_start, platform_end = _resolve_platform_alarm_times(start_time, end_time)
    start_iso, end_iso, _ = _resolve_or_prepare_alarm_times(start_time, end_time)

    all_records: list[dict[str, Any]] = []
    total = 0
    page = 1

    while len(all_records) < max_records:
        if list_api == _ALARM_API_UNPROCESSED:
            payload = build_alarm_unprocess_list_payload(
                start_time=platform_start,
                end_time=platform_end,
                filter_params=filter_params,
                status_codes=status_codes,
                page=page,
                size=page_size,
            )
        else:
            scoped_params = dict(filter_params)
            if status_codes:
                scoped_params["status"] = status_codes
            payload = build_alarm_list_filter_payload(
                start_time=start_iso or start_time,
                end_time=end_iso or end_time,
                filter_params=scoped_params,
                status_fallback=status_codes[0] if len(status_codes) == 1 else "",
                page=page,
                size=page_size,
            )

        data = call_platform_api(
            method="post",
            path=_alarm_api_path(list_api),
            data=payload,
        )
        page_total, _ = _summarize_alarm_list(data, brief_limit=0)
        if page == 1:
            total = page_total

        batch = _extract_alarm_records(data)
        if not batch:
            break
        all_records.extend(batch)
        if len(all_records) >= total or len(batch) < page_size:
            break
        page += 1

    return all_records[:max_records], total


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

    # 平台 getAlarmList / getAlarmUnprocessList 设备筛选字段为 deviceCodes[]
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


def resolve_alarm_device_filter(
    filter_params: dict[str, Any],
    *,
    device_code: str = "",
    device_name: str = "",
    hitl_tool: str = "query_alarms",
) -> tuple[list[str], str | None]:
    """
    解析告警查询的设备筛选，写回 filter_params["device_code"]。

    平台仅支持 deviceCodes[]（设备编码集合），名称需先解析为编码。
    返回 (device_codes, error_message)；无设备条件时 ([], None)。
    """
    code = str(
        device_code or filter_params.get("device_code") or filter_params.get("deviceCode") or ""
    ).strip()
    name = str(
        device_name or filter_params.get("device_name") or filter_params.get("deviceName") or ""
    ).strip()

    existing = _normalize_hitl_id_list(
        filter_params.get("deviceCodes")
        if filter_params.get("deviceCodes") not in (None, "", [])
        else filter_params.get("device_codes")
    )
    if existing and not code and not name:
        filter_params["device_code"] = existing[0] if len(existing) == 1 else ",".join(existing)
        return existing, None

    if not code and not name:
        return [], None

    from platform_mcp.runtime.tools.device import _resolve_device_code

    resolved, _record, err = _resolve_device_code(
        device_code=code,
        device_name=name,
        hitl_tool=hitl_tool,
    )
    if err or not resolved:
        return [], err or "未能解析目标设备。"

    filter_params["device_code"] = resolved
    filter_params.pop("device_name", None)
    filter_params.pop("deviceName", None)
    return [resolved], None


def _resolve_or_prepare_alarm_times(
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
        # 使用者未明确时间范围 → 必须 HITL 补参，禁止静默默认区间
        return "", "", True

    # 有输入但解析失败 → 需要 HITL
    return str(start_time or ""), str(end_time or ""), True


@tool
def query_alarms(
    start_time: str = "",
    end_time: str = "",
    alarm_level: str = "",
    status: str = "",
    device_code: str = "",
    device_name: str = "",
) -> str:
    """
    帮使用者查询告警列表（仅查询/统计，不导出）。

    参数
    ----
    start_time : str
        相对时间（「近三天」「近30分钟」）或绝对时间；原样传入，由服务端解析。
    end_time : str
        通常留空；相对时间由 resolve_alarm_time_range 自动补全。
    alarm_level : str
        报警级别筛选（映射到 alarmRankId）。
    status : str
        「未处理」→ getAlarmUnprocessList；「待确认」/「未确认」/1 → 仅 status=1；等等。
    device_code / device_name : str
        按设备筛选；平台传参为 deviceCodes[]，名称会先解析为编码。

    平台 API
    --------
    POST ``/alarm/getAlarmList`` 或 ``/alarm/getAlarmUnprocessList``（分页）。

    HITL
    ----
    时间等缺参由 ``ensure_tool_args`` / preflight 触发 ask_params（非本函数内直接 interrupt）。
    解析后仍无合法时间则返回 ok=False 摘要，不静默默认区间。

    返回（ToolResult JSON）
    ----------------------
    成功：summary 中文总数；data 含 total、items（摘要行）、queryContext（供 Workspace 翻页）。
    失败：ok=False + 平台/参数错误摘要。

    LLM 注意：使用者未明确时间仍须立即调用本工具，禁止先用自然语言追问时间。
    """
    from platform_mcp.runtime.tool_preflight import ensure_tool_args

    try:
        params = ensure_tool_args(
            "query_alarms",
            {
                "start_time": start_time,
                "end_time": end_time,
                "status": status,
                "alarm_rank_id": alarm_level,
                "device_code": device_code,
                "device_name": device_name,
            },
        )
    except ValueError as exc:
        return tool_result(ok=False, summary=str(exc))

    start_time = str(params.get("start_time", start_time))
    end_time = str(params.get("end_time", end_time))
    status_val = str(params.get("status") or status)
    alarm_level = str(params.get("alarm_rank_id") or alarm_level)
    filter_params = dict(params)

    device_codes, device_err = resolve_alarm_device_filter(
        filter_params,
        device_code=str(params.get("device_code") or device_code),
        device_name=str(params.get("device_name") or device_name),
        hitl_tool="query_alarms",
    )
    if device_err:
        return tool_result(ok=False, summary=device_err)

    start_iso, end_iso, needs_hitl = _resolve_or_prepare_alarm_times(start_time, end_time)
    if needs_hitl:
        return tool_result(
            ok=False,
            summary="告警查询时间范围无效或未选择，请重新指定时间范围。",
        )

    list_api, status_codes = _parse_hitl_status_scope(params.get("status") or status)
    if not str(params.get("status") or status or "").strip() and status_val.strip():
        list_api, status_codes = _parse_alarm_list_scope(status_val)

    try:
        records, total = _fetch_alarm_list_paginated(
            start_time=start_time,
            end_time=end_time,
            filter_params=filter_params,
            list_api=list_api,
            status_codes=status_codes,
            page_size=QUERY_ALARM_PAGE_SIZE,
            max_records=QUERY_ALARM_PAGE_SIZE,
        )
    except PlatformApiError as exc:
        return tool_result(ok=False, summary=str(exc))
    except ValueError as exc:
        return tool_result(ok=False, summary=str(exc))

    brief = [_map_alarm_brief_item(item) for item in records]
    platform_start, platform_end = _resolve_platform_alarm_times(start_time, end_time)

    scope_label = "未处理" if list_api == _ALARM_API_UNPROCESSED else "告警"
    device_hint = f"（设备 {device_codes[0]}）" if len(device_codes) == 1 else ""
    if len(device_codes) > 1:
        device_hint = f"（{len(device_codes)} 台设备）"
    summary = f"共查询到 {total} 条{scope_label}{device_hint}（展示前 {len(brief)} 条摘要）。"
    query_context = {
        "startTime": platform_start,
        "endTime": platform_end,
        "deviceCodes": device_codes,
        "variableNames": [],
        "alarmCategoryId": _normalize_hitl_id_list(filter_params.get("alarm_category_id")),
        "alarmRankId": _normalize_hitl_id_list(filter_params.get("alarm_rank_id") or alarm_level),
        "status": status_codes,
        "listApi": list_api,
    }
    return tool_result(
        ok=True,
        summary=summary,
        data={
            "total": total,
            "items": brief,
            "page": 1,
            "pageSize": QUERY_ALARM_PAGE_SIZE,
            "queryContext": query_context,
        },
    )


@tool
def get_alarm_detail(alarm_id: str = "") -> str:
    """
    帮使用者查看单条告警详情。

    参数
    ----
    alarm_id : str
        业务告警编号；缺省时 preflight / HITL 表单追问。

    平台 API
    --------
    POST ``/alarm/getAlarmList``，body 带 ``ids=[alarm_id]`` + 宽时间窗。

    HITL
    ----
    缺 alarm_id → ask_params（字段见 _GET_DETAIL_FIELDS / preflight schema）。

    返回（ToolResult JSON）
    ----------------------
    成功：summary 一行摘要；data=完整记录；client_action=openModal(alarmDetail)。
    未找到：ok=False。
    """
    from platform_mcp.runtime.tool_preflight import ensure_tool_args

    try:
        params = ensure_tool_args("get_alarm_detail", {"alarm_id": alarm_id})
    except ValueError as exc:
        return tool_result(ok=False, summary=str(exc))
    aid = str(params["alarm_id"]).strip()

    try:
        # 用 ids 筛选 + 宽时间范围，等价于按 ID 查单条
        data = call_platform_api(
            method="post",
            path="/alarm/getAlarmList",
            data={
                "ids": [aid],
                "page": 1,
                "size": 1,
                "startTime": "2000-01-01 00:00:00",
                "endTime": "2099-12-31 23:59:59",
                "deviceCodes": [],
                "variableNames": [],
                "alarmCategoryId": [],
                "alarmRankId": [],
                "status": [],
            },
        )
    except PlatformApiError as exc:
        return tool_result(ok=False, summary=str(exc))

    _total, brief = _summarize_alarm_list(data)
    if not brief:
        return tool_result(ok=False, summary=f"未找到编号为 {aid} 的告警，请核对后重试")

    record = brief[0]
    # brief 字段较少；从原始响应取完整记录（含 alarmPic 等）
    full_record = record
    if isinstance(data, dict):
        records = data.get("records") or data.get("list") or []
        if records and isinstance(records[0], dict):
            full_record = records[0]

    summary = (
        f"告警 {aid}：设备 {full_record.get('deviceName', '-')}，"
        f"变量 {full_record.get('variableName', '-')}，"
        f"时间 {full_record.get('startTime', '-')}，"
        f"状态 {full_record.get('status', '-')}。"
    )
    return tool_result(
        ok=True,
        summary=summary,
        data=full_record,
        client_action={
            "action": "openModal",
            "modal": "alarmDetail",
            "params": {"alarmId": aid, "record": full_record},
        },
    )


# batch_confirm_alarms 无 alarm_ids 时复用告警查询 HITL 字段
_BATCH_CONFIRM_FIELDS = _QUERY_ALARM_FIELDS


def _alarm_status_code(item: dict[str, Any]) -> int | None:
    """解析单条告警 status 数字码。"""
    raw = item.get("status")
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except TypeError, ValueError:
        return None


def _summarize_status_breakdown(records: list[dict[str, Any]]) -> str:
    """按 status 统计条数，生成可读摘要。"""
    counts: dict[int, int] = {1: 0, 2: 0, 3: 0}
    for item in records:
        code = _alarm_status_code(item)
        if code in counts:
            counts[code] += 1
    parts: list[str] = []
    if counts[1]:
        parts.append(f"待确认 {counts[1]} 条")
    if counts[2]:
        parts.append(f"已确认 {counts[2]} 条")
    if counts[3]:
        parts.append(f"已处理 {counts[3]} 条")
    return "、".join(parts) if parts else "状态未知"


def _build_batch_write_empty_message(
    *,
    operation: str,
    source_label: str,
    target_label: str,
    raw_records: list[dict[str, Any]],
    alternate_hint: str = "",
) -> str:
    """
    批量写操作无可执行记录时的说明。

    确认：待确认(1) → 已确认(2)
    处理：待确认(1) 或 已确认(2) → 已处理(3)
    """
    breakdown = _summarize_status_breakdown(raw_records)
    base = (
        f"指定范围内共 {len(raw_records)} 条告警（{breakdown}）。"
        f"「{operation}」仅适用于「{source_label}」告警，执行后将变为「{target_label}」。"
        f"当前无「{source_label}」告警可{operation}。"
    )
    if alternate_hint:
        base += f" {alternate_hint}"
    return base


def _is_process_eligible_record(item: dict[str, Any]) -> bool:
    """是否可执行批量处理：待确认(1) 或 已确认(2)。"""
    code = _alarm_status_code(item)
    if code in (1, 2):
        return True
    if code is None:
        name = _format_alarm_status(item)
        return "待确认" in name or "已确认" in name
    return False


def _is_confirmed_record(item: dict[str, Any]) -> bool:
    """是否「已确认」状态（status=2）。"""
    return _alarm_status_code(item) == 2


def _is_pending_confirm_record(item: dict[str, Any]) -> bool:
    """仅允许确认「待确认」状态（status=1）的告警。"""
    raw = item.get("status")
    if raw is None or raw == "":
        name = _format_alarm_status(item)
        return "待确认" in name
    try:
        return int(raw) == 1
    except TypeError, ValueError:
        return "待确认" in str(raw)


def _resolve_platform_alarm_times(start_time: str, end_time: str) -> tuple[str, str]:
    """相对时间 → 平台 YYYY-MM-DD HH:mm:ss（与 query_alarms 一致）。"""
    start_iso, end_iso, needs_hitl = _resolve_or_prepare_alarm_times(start_time, end_time)
    if needs_hitl:
        raise ValueError("告警时间范围无效或未选择，请重新指定时间范围。")
    return _to_platform_time(start_iso), _to_platform_time(end_iso)


def _parse_alarm_ids(raw: str) -> list[str]:
    """
    解析逗号、空格或中文顿号分隔的告警编号字符串。

    例如 "1, 2，3、4" → ["1", "2", "3", "4"]
    """
    if not raw or not str(raw).strip():
        return []
    normalized = str(raw).replace("，", ",").replace("、", ",")
    return [part.strip() for part in normalized.split(",") if part.strip()]


def _fetch_alarm_records_by_ids(alarm_ids: list[str]) -> list[dict[str, Any]]:
    """按编号拉取完整告警行（confirmAlarm 需要完整对象）。"""
    payload: dict[str, Any] = {
        "ids": alarm_ids,
        "page": 1,
        "size": max(len(alarm_ids), BATCH_CONFIRM_PAGE_SIZE),
        "startTime": "2000-01-01 00:00:00",
        "endTime": "2099-12-31 23:59:59",
        "deviceCodes": [],
        "variableNames": [],
        "alarmCategoryId": [],
        "alarmRankId": [],
        "status": [],
    }
    data = call_platform_api(
        method="post",
        path="/alarm/getAlarmList",
        data=payload,
    )
    return _extract_alarm_records(data)


def _extract_alarm_records(data: Any) -> list[dict[str, Any]]:
    """从平台分页响应提取 records 列表。"""
    if isinstance(data, dict):
        records = data.get("records") or data.get("list") or data.get("rows") or []
    elif isinstance(data, list):
        records = data
    else:
        records = []
    return [item for item in records if isinstance(item, dict)]


def _fetch_alarm_records_by_filters(
    *,
    start_time: str,
    end_time: str,
    filter_params: dict[str, Any],
    list_api: str,
    status_codes: list[str],
    eligible_predicate,
    max_records: int = BATCH_CONFIRM_FETCH_MAX,
) -> tuple[list[dict[str, Any]], int, list[dict[str, Any]]]:
    """
    按范围拉取告警并筛出符合批量写操作条件的记录。

    返回 (可执行记录, 列表 total, 原始拉取记录)。
    """
    all_records, total = _fetch_alarm_list_paginated(
        start_time=start_time,
        end_time=end_time,
        filter_params=filter_params,
        list_api=list_api,
        status_codes=status_codes,
        page_size=BATCH_CONFIRM_PAGE_SIZE,
        max_records=max_records,
    )
    eligible = [item for item in all_records if eligible_predicate(item)]
    return eligible[:max_records], total, all_records


def _fetch_alarm_records(
    *,
    alarm_ids: list[str] | None = None,
    start_time: str = "",
    end_time: str = "",
    filter_params: dict[str, Any] | None = None,
    list_api: str = _ALARM_API_LIST,
    status_codes: list[str] | None = None,
    eligible_predicate=_is_pending_confirm_record,
) -> tuple[list[dict[str, Any]], int, list[dict[str, Any]]]:
    """
    从平台拉取待确认的完整告警记录（兼容旧调用签名）。

    alarm_ids 优先；否则按时间范围 + 与前端一致的筛选条件。
    """
    if alarm_ids:
        records = _fetch_alarm_records_by_ids(alarm_ids)
        eligible = [item for item in records if eligible_predicate(item)]
        return eligible, len(eligible), records

    params = filter_params or {}
    codes = list(status_codes or [])
    return _fetch_alarm_records_by_filters(
        start_time=start_time,
        end_time=end_time,
        filter_params=params,
        list_api=list_api,
        status_codes=codes,
        eligible_predicate=eligible_predicate,
    )


def _build_confirm_message(
    records: list[dict[str, Any]],
    *,
    platform_total: int = 0,
    raw_records: list[dict[str, Any]] | None = None,
    list_api: str = _ALARM_API_LIST,
) -> str:
    """
    构造批量确认前的 HITL 确认文案：总条数 + 前 5 条摘要。
    """
    count = len(records)
    hints: list[str] = []
    if list_api == _ALARM_API_UNPROCESSED and raw_records and len(raw_records) > count:
        hints.append(f"未处理 {len(raw_records)} 条，其中待确认 {count} 条")
    elif platform_total and platform_total != count:
        hints.append(f"共 {platform_total} 条，待确认 {count} 条")
    hint_text = f"（{'；'.join(hints)}）" if hints else ""
    lines = [
        f"即将批量确认 {count} 条「待确认」告警{hint_text}，确认后将变为「已确认」，是否继续？"
    ]
    for item in records[:5]:
        lines.append(
            f"- #{item.get('id')} {item.get('deviceName', '-')} / "
            f"{item.get('variableName', '-')} / {item.get('startTime', '-')} "
            f"（{_format_alarm_status(item)}）"
        )
    if count > 5:
        lines.append(f"… 另有 {count - 5} 条未列出")
    return "\n".join(lines)


def _prepare_confirm_records(
    records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], str | None]:
    """
    对齐前端 confirmAlarm：补全 confirmPerson，校验 alarmCategoryId。

    返回 (payload, error_message)；error_message 非空表示不可提交。
    """
    username = get_username_from_token(current_auth_token.get()) or "root"
    prepared: list[dict[str, Any]] = []
    missing_category: list[str] = []

    for item in records:
        row = dict(item)
        if not str(row.get("confirmPerson") or "").strip():
            row["confirmPerson"] = username

        category_id = row.get("alarmCategoryId")
        if category_id in (None, "", 0):
            missing_category.append(str(row.get("id") or "?"))
            continue
        prepared.append(row)

    if missing_category:
        return [], (
            f"以下告警缺少报警类型（alarmCategoryId），无法确认："
            f"{', '.join(missing_category[:5])}"
            f"{'…' if len(missing_category) > 5 else ''}。"
            f"请在平台报警信息查询页手动确认，或指定明确编号后重试。"
        )
    return prepared, None


def _call_confirm_alarm_api(records: list[dict[str, Any]]) -> str:
    """
    调用平台 POST /alarm/confirmAlarm 执行批量确认。
    """
    payload, prep_error = _prepare_confirm_records(records)
    if prep_error:
        return tool_result(ok=False, summary=prep_error)

    try:
        call_platform_api(
            method="post",
            path="/alarm/confirmAlarm",
            data=payload,
        )
        return tool_result(
            ok=True,
            summary=f"已成功将 {len(payload)} 条告警「确认」为已确认状态。",
            data={"confirmed_count": len(payload), "ids": [r.get("id") for r in payload]},
            client_action={
                "action": "refresh",
                "target": "alarmList",
            },
        )
    except PlatformApiError as exc:
        return tool_result(ok=False, summary=str(exc))


def _resolve_batch_write_fetch_scope(
    status_raw: Any,
    *,
    operation: str,
) -> tuple[str, list[str]]:
    """
    解析批量写操作的列表 API 与 status 筛选。

    operation:
        confirm — 默认待确认(1)，getAlarmList
        process — 默认未处理全集(1+2)，getAlarmUnprocessList
    """
    if not str(status_raw or "").strip():
        if operation == "confirm":
            return _ALARM_API_LIST, ["1"]
        return _ALARM_API_UNPROCESSED, []

    list_api, status_codes = _parse_hitl_status_scope(status_raw)
    if list_api == _ALARM_API_UNPROCESSED and not status_codes:
        return list_api, []
    if list_api == _ALARM_API_LIST and not status_codes:
        return _parse_alarm_list_scope(str(status_raw))
    return list_api, status_codes


def _prepare_process_records(
    records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], str | None]:
    """
    对齐前端 processAlarm：
    - 待确认(1)：需 confirmPerson + alarmCategoryId（同「立即处理」）
    - 已确认(2)：补全 processPerson
    """
    username = get_username_from_token(current_auth_token.get()) or "root"
    prepared: list[dict[str, Any]] = []
    missing_category: list[str] = []

    for item in records:
        row = dict(item)
        if not str(row.get("processPerson") or "").strip():
            row["processPerson"] = username

        code = _alarm_status_code(item)
        if code == 1 or (code is None and "待确认" in _format_alarm_status(item)):
            if not str(row.get("confirmPerson") or "").strip():
                row["confirmPerson"] = username
            category_id = row.get("alarmCategoryId")
            if category_id in (None, "", 0):
                missing_category.append(str(row.get("id") or "?"))
                continue

        prepared.append(row)

    if missing_category:
        return [], (
            f"以下「待确认」告警缺少报警类型（alarmCategoryId），无法处理："
            f"{', '.join(missing_category[:5])}"
            f"{'…' if len(missing_category) > 5 else ''}。"
            f"请在平台报警信息查询页手动处理，或先确认后再处理。"
        )
    return prepared, None


def _build_process_message(
    records: list[dict[str, Any]],
    *,
    raw_records: list[dict[str, Any]] | None = None,
    list_api: str = _ALARM_API_LIST,
) -> str:
    """构造批量处理前的 HITL 确认文案（总条数拆分待确认/已确认 + 前 5 条摘要）。"""
    count = len(records)
    pending_n = sum(1 for r in records if _alarm_status_code(r) == 1)
    confirmed_n = sum(1 for r in records if _alarm_status_code(r) == 2)
    hints: list[str] = []
    if pending_n:
        hints.append(f"待确认 {pending_n} 条")
    if confirmed_n:
        hints.append(f"已确认 {confirmed_n} 条")
    scope_hint = f"（{'、'.join(hints)}）" if hints else ""
    if list_api == _ALARM_API_UNPROCESSED and raw_records and len(raw_records) > count:
        scope_hint = f"（未处理 {len(raw_records)} 条，可处理 {count} 条）"

    lines = [f"即将批量处理 {count} 条告警{scope_hint}，处理后将变为「已处理」，是否继续？"]
    for item in records[:5]:
        lines.append(
            f"- #{item.get('id')} {item.get('deviceName', '-')} / "
            f"{item.get('variableName', '-')} / {item.get('startTime', '-')} "
            f"（{_format_alarm_status(item)}）"
        )
    if count > 5:
        lines.append(f"… 另有 {count - 5} 条未列出")
    return "\n".join(lines)


def _call_process_alarm_api(records: list[dict[str, Any]]) -> str:
    """调用平台 POST /alarm/processAlarm（待确认/已确认 → 已处理）。"""
    payload, prep_error = _prepare_process_records(records)
    if prep_error:
        return tool_result(ok=False, summary=prep_error)

    try:
        call_platform_api(
            method="post",
            path="/alarm/processAlarm",
            data=payload,
        )
        return tool_result(
            ok=True,
            summary=f"已成功将 {len(payload)} 条告警「处理」为已处理状态。",
            data={"processed_count": len(payload), "ids": [r.get("id") for r in payload]},
            client_action={"action": "refresh", "target": "alarmList"},
        )
    except PlatformApiError as exc:
        return tool_result(ok=False, summary=str(exc))


@tool
def batch_confirm_alarms(
    alarm_ids: str = "",
    start_time: str = "",
    end_time: str = "",
    status: str = "",
) -> str:
    """
    帮使用者批量确认告警（高风险，必须先经使用者 HITL 批准）。

    参数
    ----
    alarm_ids : str
        逗号/顿号分隔的编号；有则优先按 ID 拉取。
    start_time / end_time / status : str
        无 ID 时按条件筛选；status 支持「未处理」「待确认」等。

    平台 API
    --------
    1) 列表：getAlarmList / getAlarmUnprocessList（筛出 status=1）
    2) 写：POST ``/alarm/confirmAlarm``（待确认 → 已确认）

    HITL
    ----
    - 无 ID 且缺时间等：preflight ask_params
    - 有可确认记录后：``ask_user_confirm``；拒绝 → ok=False 且 user_cancelled=True，不调确认 API

    返回（ToolResult JSON）
    ----------------------
    成功：confirmed_count + ids；client_action refresh alarmList。

    产品语义：确认 ≠ 处理；处理请用 batch_process_alarms。同一轮只应调用一次本工具。
    """
    parsed_ids = _parse_alarm_ids(alarm_ids)
    filter_params: dict[str, Any] = {}

    if not parsed_ids:
        from platform_mcp.runtime.tool_preflight import ensure_tool_args

        try:
            params = ensure_tool_args(
                "batch_confirm_alarms",
                {
                    "start_time": start_time,
                    "end_time": end_time,
                    "status": status,
                },
            )
        except ValueError as exc:
            return tool_result(ok=False, summary=str(exc))

        start_time = str(params.get("start_time", start_time))
        end_time = str(params.get("end_time", end_time))
        filter_params = params
        list_api, status_codes = _resolve_batch_write_fetch_scope(
            params.get("status") or status,
            operation="confirm",
        )
    else:
        list_api, status_codes = _ALARM_API_LIST, ["1"]

    try:
        records, platform_total, raw_records = _fetch_alarm_records(
            alarm_ids=parsed_ids or None,
            start_time=start_time,
            end_time=end_time,
            filter_params=filter_params,
            list_api=list_api,
            status_codes=status_codes,
            eligible_predicate=_is_pending_confirm_record,
        )
    except ValueError as exc:
        return tool_result(ok=False, summary=str(exc))
    except PlatformApiError as exc:
        return tool_result(ok=False, summary=str(exc))

    if not records:
        if parsed_ids:
            return tool_result(
                ok=False,
                summary=(
                    f"未找到编号为 {', '.join(parsed_ids)} 的「待确认」告警。"
                    f"确认操作将待确认变为已确认，请核对编号与状态。"
                ),
            )
        if raw_records:
            return tool_result(
                ok=False,
                summary=_build_batch_write_empty_message(
                    operation="确认",
                    source_label="待确认",
                    target_label="已确认",
                    raw_records=raw_records,
                    alternate_hint=(
                        "若仅需将「待确认」变为「已确认」（不直接处理），"
                        "请说「批量确认近三天未处理告警」。"
                    ),
                ),
            )
        return tool_result(
            ok=False,
            summary="在指定时间范围内未找到待确认告警，无需确认。",
        )

    approved = ask_user_confirm(
        tool="batch_confirm_alarms",
        message=_build_confirm_message(
            records,
            platform_total=platform_total,
            raw_records=raw_records,
            list_api=list_api,
        ),
    )
    if not approved:
        return tool_result(
            ok=False,
            summary="使用者已取消批量确认。",
            user_cancelled=True,
        )

    return _call_confirm_alarm_api(records)


@tool
def batch_process_alarms(
    alarm_ids: str = "",
    start_time: str = "",
    end_time: str = "",
    status: str = "",
) -> str:
    """
    帮使用者批量处理告警（高风险，必须先经使用者 HITL 批准）。

    参数
    ----
    alarm_ids / start_time / end_time / status
        定位方式同 batch_confirm_alarms；默认可处理范围常为「未处理」全集。

    平台 API
    --------
    1) 列表：getAlarmList / getAlarmUnprocessList（筛 status 1 或 2）
    2) 写：POST ``/alarm/processAlarm``（→ 已处理）

    HITL
    ----
    有可处理记录后 ``ask_user_confirm``；拒绝 → user_cancelled=True，不调 processAlarm。
    待确认记录缺少 alarmCategoryId 时预处理失败，返回可读错误（对齐前端立即处理）。

    返回（ToolResult JSON）
    ----------------------
    成功：processed_count + ids；client_action refresh alarmList。

    产品语义：待确认可直接处理；已确认只能处理不能再确认。
    """
    parsed_ids = _parse_alarm_ids(alarm_ids)
    filter_params: dict[str, Any] = {}

    if not parsed_ids:
        from platform_mcp.runtime.tool_preflight import ensure_tool_args

        try:
            params = ensure_tool_args(
                "batch_process_alarms",
                {
                    "start_time": start_time,
                    "end_time": end_time,
                    "status": status,
                },
            )
        except ValueError as exc:
            return tool_result(ok=False, summary=str(exc))

        start_time = str(params.get("start_time", start_time))
        end_time = str(params.get("end_time", end_time))
        filter_params = params
        list_api, status_codes = _resolve_batch_write_fetch_scope(
            params.get("status") or status,
            operation="process",
        )
    else:
        list_api, status_codes = _ALARM_API_LIST, []

    try:
        records, _platform_total, raw_records = _fetch_alarm_records(
            alarm_ids=parsed_ids or None,
            start_time=start_time,
            end_time=end_time,
            filter_params=filter_params,
            list_api=list_api,
            status_codes=status_codes,
            eligible_predicate=_is_process_eligible_record,
        )
    except ValueError as exc:
        return tool_result(ok=False, summary=str(exc))
    except PlatformApiError as exc:
        return tool_result(ok=False, summary=str(exc))

    if not records:
        if parsed_ids:
            return tool_result(
                ok=False,
                summary=(
                    f"未找到编号为 {', '.join(parsed_ids)} 的可处理告警。"
                    f"处理适用于「待确认」或「已确认」状态。"
                ),
            )
        if raw_records:
            return tool_result(
                ok=False,
                summary=_build_batch_write_empty_message(
                    operation="处理",
                    source_label="待确认或已确认",
                    target_label="已处理",
                    raw_records=raw_records,
                ),
            )
        return tool_result(
            ok=False,
            summary="在指定时间范围内未找到可处理的未处理告警。",
        )

    approved = ask_user_confirm(
        tool="batch_process_alarms",
        message=_build_process_message(
            records,
            raw_records=raw_records,
            list_api=list_api,
        ),
    )
    if not approved:
        return tool_result(
            ok=False,
            summary="使用者已取消批量处理。",
            user_cancelled=True,
        )

    return _call_process_alarm_api(records)
