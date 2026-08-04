"""
报表 / 文件导出 Server Tools 模块

文件职责
--------
``download_file`` 按 ``resource`` 分发到各导出实现：
- ``alarm_report``：告警 Excel（计数 → HITL 确认 → client_action.download）
- ``sentry_handover``：岗哨交接 Excel（同上模式）
- ``duty_info``：值班信息 Excel（同上模式）
- ``duty_manage``：值班管理 Excel（同上模式）
- ``acs_record``：出入信息 Excel（同上模式，可选 personId）

白话概念
--------
Agent 不直接把 Excel 流写进 SSE；而是生成「带筛选条件的下载链接」，
前端用用户 Token 去请求平台导出接口，体验与业务页导出一致。

在 Agent 流程中的位置
--------------------
  LLM 调用 download_file
    → ensure_tool_args（缺时间 → ask_params）
    → 按 resource 分发 execute_*_export
    → 列表计数 → ask_user_confirm → tool_result + download URL

HITL
----
- 缺参：preflight ask_params
- 有可导出条数后：ask_user_confirm；拒绝 → user_cancelled=True
- 本轮被压制：current_turn_suppressed_tools 含 download_file 时直接失败（防串轮导出）
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode  # 将 dict 编码为 URL 查询字符串

from langchain_core.tools import tool

from contracts.alarm_params import to_platform_time
from contracts.export_infer import (
    EXPORT_ALARM_BATCH_MAX,
)
from contracts.hitl import ask_user_confirm
from contracts.platform_client import PlatformApiError, call_platform_api
from contracts.result import tool_result
from contracts.time_range import resolve_alarm_time_range
from platform_mcp.runtime.tools.alarm import (
    _ALARM_API_UNPROCESSED,
    _apply_alarm_filter_fields,
    count_alarms_matching_filters,
    export_status_codes_for_scope,
    resolve_alarm_filter_scope,
)

# 已落地的导出 resource（扩展新类型时同步 catalog enum 与本集合）
SUPPORTED_EXPORT_RESOURCES = frozenset(
    {"alarm_report", "sentry_handover", "duty_info", "duty_manage", "acs_record"}
)


def _build_app_download_url(path: str, params: dict[str, Any]) -> str:
    """
    构造前端可带鉴权下载的相对 URL（走 Umi 代理 /api/app）。

    参数：
        path: 平台 API 路径，如 "/alarm/exportAlarm"
        params: 导出接口所需的查询/body 参数字典

    返回：
        如 "/api/app/alarm/exportAlarm?startTime=...&endTime=..."
    """
    flat: dict[str, Any] = {}
    for key, value in params.items():
        if value is None or value == "":
            continue
        if isinstance(value, list) and not value:
            continue
        flat[key] = value
    qs = urlencode(flat, doseq=True)
    base = path if path.startswith("/") else f"/{path}"
    return f"/api/app{base}?{qs}" if qs else f"/api/app{base}"


def plan_alarm_export_batches(total: int) -> list[tuple[int, int]]:
    """
    规划 exportAlarm 的 (page, size) 批次。

    参数:
        total: 符合条件的告警总数

    返回:
        例如 total=60 → [(1, 60)]；total=65000 → [(1, 30000), (2, 30000), (3, 5000)]
    """
    if total <= 0:
        return []

    batches: list[tuple[int, int]] = []
    exported = 0
    page = 1
    while exported < total:
        batch_size = min(EXPORT_ALARM_BATCH_MAX, total - exported)
        batches.append((page, batch_size))
        exported += batch_size
        page += 1
    return batches


def _build_export_download_actions(
    *,
    base_params: dict[str, Any],
    batches: list[tuple[int, int]],
    start_fmt: str,
    end_fmt: str,
    export_path: str = "/alarm/exportAlarm",
    filename_prefix: str = "告警记录",
) -> list[dict[str, str]]:
    """根据批次生成前端 download client_action 列表。"""
    date_label = f"{start_fmt[:10]}_{end_fmt[:10]}"
    downloads: list[dict[str, str]] = []
    batch_count = len(batches)

    for index, (page, size) in enumerate(batches, 1):
        export_params = {**base_params, "page": page, "size": size}
        url = _build_app_download_url(export_path, export_params)
        if batch_count == 1:
            filename = f"{filename_prefix}_{date_label}.xlsx"
        else:
            filename = f"{filename_prefix}_{date_label}_第{index}批共{batch_count}.xlsx"
        downloads.append({"action": "download", "url": url, "filename": filename})
    return downloads


def execute_alarm_export(
    *,
    start_time: str,
    end_time: str,
    status: str | list[str] = "",
    filter_params: dict[str, Any] | None = None,
    require_confirm: bool = True,
) -> str:
    """
    执行告警 Excel 导出的核心逻辑（供 @tool 与直达路径共用）。

    参数
    ----
    start_time / end_time : str
        已由上层补参或相对时间原文。
    status / filter_params
        筛选条件；与 query_alarms 共用 resolve / count。
    require_confirm : bool
        False 时跳过 ask_user_confirm（编排层已确认等场景）。

    流程
    ----
    1. 解析时间 → 平台格式
    2. count_alarms_matching_filters 统计
    3. plan_alarm_export_batches（单次最多 EXPORT_ALARM_BATCH_MAX）
    4. 可选 HITL confirm
    5. 拼 download URL，返回 tool_result

    返回
    ----
    ToolResult JSON 字符串（成功含 client_action 或 client_actions）。
    """
    resolved = resolve_alarm_time_range(start_time, end_time)
    if resolved:
        start_time, end_time = resolved

    start_fmt = to_platform_time(str(start_time))
    end_fmt = to_platform_time(str(end_time))
    filters = filter_params or {}
    alarm_level = filters.get("alarm_rank_id") or filters.get("alarm_level") or ""

    list_api, status_codes = resolve_alarm_filter_scope(filters, status_fallback=status)
    export_status = export_status_codes_for_scope(list_api, status_codes)

    try:
        total = count_alarms_matching_filters(
            start_time=start_time,
            end_time=end_time,
            filter_params=filters,
            status_fallback=status,
            alarm_level=alarm_level,
        )
    except PlatformApiError as exc:
        return tool_result(ok=False, summary=str(exc))

    if total <= 0:
        return tool_result(ok=False, summary="当前筛选条件下没有可导出的告警记录。")

    batches = plan_alarm_export_batches(total)
    if not batches:
        return tool_result(ok=False, summary="当前筛选条件下没有可导出的告警记录。")

    base_params: dict[str, Any] = {
        "startTime": start_fmt,
        "endTime": end_fmt,
        "deviceCodes": [],
        "variableNames": [],
        "alarmCategoryId": [],
        "alarmRankId": [],
        "status": export_status,
    }
    # 类别/级别筛选；status 已按范围解析，避免 _normalize_hitl_status_list 剥掉「未处理」
    filters_without_status = {k: v for k, v in filters.items() if k != "status"}
    _apply_alarm_filter_fields(
        base_params,
        filters_without_status,
        status_fallback="",
        alarm_level=alarm_level,
    )
    base_params["status"] = export_status

    range_label = f"{start_fmt} 至 {end_fmt}"
    if list_api == _ALARM_API_UNPROCESSED:
        if status_codes:
            range_label += f"，状态：{','.join(status_codes)}"
        else:
            range_label += "，状态：未处理"
    elif export_status:
        range_label += f"，状态：{','.join(export_status)}"

    if len(batches) == 1:
        confirm_message = f"将导出 {total} 条告警记录（{range_label}），是否继续？"
    else:
        confirm_message = (
            f"共 {total} 条告警，将分 {len(batches)} 个 Excel 文件导出"
            f"（每批最多 {EXPORT_ALARM_BATCH_MAX} 条，{range_label}），是否继续？"
        )

    if require_confirm:
        approved = ask_user_confirm(
            tool="download_file",
            message=confirm_message,
        )
        if not approved:
            return tool_result(
                ok=False,
                summary="使用者已取消导出。",
                user_cancelled=True,
            )

    downloads = _build_export_download_actions(
        base_params=base_params,
        batches=batches,
        start_fmt=start_fmt,
        end_fmt=end_fmt,
        export_path="/alarm/exportAlarm",
        filename_prefix="告警记录",
    )

    if len(downloads) == 1:
        summary = f"已准备导出 {total} 条告警（{range_label}），正在触发浏览器下载。"
        return tool_result(
            ok=True,
            summary=summary,
            data={"total": total, "batchCount": 1, "resource": "alarm_report"},
            client_action=downloads[0],
        )

    summary = (
        f"共 {total} 条告警，已准备 {len(downloads)} 个导出文件（{range_label}），"
        "将依次触发浏览器下载。"
    )
    return tool_result(
        ok=True,
        summary=summary,
        data={"total": total, "batchCount": len(downloads), "resource": "alarm_report"},
        client_actions=downloads,
    )


def _count_platform_list_total(*, list_path: str, payload: dict[str, Any]) -> int:
    """调用平台 POST 列表接口取 total（page/size 仅满足分页协议）。"""
    data = call_platform_api(method="post", path=list_path, data=payload)
    if isinstance(data, dict):
        total = data.get("total")
        if total is None:
            total = data.get("totalCount")
        if total is not None:
            return int(total)
        records = data.get("list") or data.get("records") or data.get("items") or []
        if isinstance(records, list):
            return len(records)
    if isinstance(data, list):
        return len(data)
    return 0


def execute_time_range_duty_export(
    *,
    resource: str,
    start_time: str,
    end_time: str,
    list_path: str,
    export_path: str,
    filename_prefix: str,
    record_label: str,
    require_confirm: bool = True,
    extra_params: dict[str, Any] | None = None,
    range_extra: str = "",
) -> str:
    """
    通用：按时间范围导出 duty 类 Excel（计数 → confirm → download URL）。

    供岗哨交接、值班信息等仅时间筛选的导出复用。
    """
    resolved = resolve_alarm_time_range(start_time, end_time)
    if resolved:
        start_time, end_time = resolved

    start_fmt = to_platform_time(str(start_time))
    end_fmt = to_platform_time(str(end_time))
    extras = extra_params or {}

    count_payload: dict[str, Any] = {
        "page": 1,
        "size": 1,
        "startTime": start_fmt,
        "endTime": end_fmt,
        **extras,
    }
    try:
        total = _count_platform_list_total(list_path=list_path, payload=count_payload)
    except PlatformApiError as exc:
        return tool_result(ok=False, summary=str(exc))

    if total <= 0:
        return tool_result(
            ok=False,
            summary=f"当前筛选条件下没有可导出的{record_label}。",
        )

    range_label = f"{start_fmt} 至 {end_fmt}{range_extra}"
    confirm_message = f"将导出 {total} 条{record_label}（{range_label}），是否继续？"
    if require_confirm:
        approved = ask_user_confirm(tool="download_file", message=confirm_message)
        if not approved:
            return tool_result(
                ok=False,
                summary="使用者已取消导出。",
                user_cancelled=True,
            )

    base_params: dict[str, Any] = {
        "startTime": start_fmt,
        "endTime": end_fmt,
        **extras,
    }
    downloads = _build_export_download_actions(
        base_params=base_params,
        batches=[(1, total)],
        start_fmt=start_fmt,
        end_fmt=end_fmt,
        export_path=export_path,
        filename_prefix=filename_prefix,
    )
    summary = f"已准备导出 {total} 条{record_label}（{range_label}），正在触发浏览器下载。"
    return tool_result(
        ok=True,
        summary=summary,
        data={"total": total, "batchCount": 1, "resource": resource},
        client_action=downloads[0],
    )


def execute_sentry_handover_export(
    *,
    start_time: str,
    end_time: str,
    sentry_id: str = "",
    require_confirm: bool = True,
) -> str:
    """
    执行岗哨交接 Excel 导出。

    平台 API
    --------
    - 计数：POST /duty/getSentryHandoverList
    - 下载：GET /duty/exportSentryHandover（前端带 Token）

    筛选：必填时间；可选 sentryId。
    """
    sid = str(sentry_id or "").strip()
    extras: dict[str, Any] = {}
    range_extra = ""
    if sid:
        extras["sentryId"] = sid
        range_extra = f"，岗哨 ID：{sid}"

    return execute_time_range_duty_export(
        resource="sentry_handover",
        start_time=start_time,
        end_time=end_time,
        list_path="/duty/getSentryHandoverList",
        export_path="/duty/exportSentryHandover",
        filename_prefix="岗哨交接",
        record_label="岗哨交接记录",
        require_confirm=require_confirm,
        extra_params=extras or None,
        range_extra=range_extra,
    )


def execute_duty_info_export(
    *,
    start_time: str,
    end_time: str,
    require_confirm: bool = True,
) -> str:
    """
    执行值班信息 Excel 导出。

    平台 API
    --------
    - 计数：POST /duty/getDutyInfoList
    - 下载：GET /duty/exportDutyInfo（前端带 Token）

    筛选：必填时间范围。
    """
    return execute_time_range_duty_export(
        resource="duty_info",
        start_time=start_time,
        end_time=end_time,
        list_path="/duty/getDutyInfoList",
        export_path="/duty/exportDutyInfo",
        filename_prefix="值班信息",
        record_label="值班信息",
        require_confirm=require_confirm,
    )


def execute_duty_manage_export(
    *,
    start_time: str,
    end_time: str,
    require_confirm: bool = True,
) -> str:
    """执行值班管理 Excel 导出（POST getDutyManageList → GET exportDutyManage）。"""
    return execute_time_range_duty_export(
        resource="duty_manage",
        start_time=start_time,
        end_time=end_time,
        list_path="/duty/getDutyManageList",
        export_path="/duty/exportDutyManage",
        filename_prefix="值班管理",
        record_label="值班管理",
        require_confirm=require_confirm,
    )


def execute_acs_record_export(
    *,
    start_time: str,
    end_time: str,
    person_id: str = "",
    require_confirm: bool = True,
) -> str:
    """
    执行出入信息 Excel 导出。

    平台 API
    --------
    - 计数：POST /acs/getAcsRecordList
    - 下载：GET /acs/exportAcsRecord

    筛选：必填时间；可选 personId。
    """
    pid = str(person_id or "").strip()
    extras: dict[str, Any] = {}
    range_extra = ""
    if pid:
        extras["personId"] = pid
        range_extra = f"，人员 ID：{pid}"

    return execute_time_range_duty_export(
        resource="acs_record",
        start_time=start_time,
        end_time=end_time,
        list_path="/acs/getAcsRecordList",
        export_path="/acs/exportAcsRecord",
        filename_prefix="出入信息",
        record_label="出入信息",
        require_confirm=require_confirm,
        extra_params=extras or None,
        range_extra=range_extra,
    )


@tool
def download_file(
    resource: str = "",
    start_time: str = "",
    end_time: str = "",
    status: str | list[str] = "",
    device_code: str = "",
    device_name: str = "",
    sentry_id: str = "",
    person_id: str = "",
) -> str:
    """
    帮使用者下载平台报表/导出文件（LangChain Tool）。

    参数
    ----
    resource : str
        ``alarm_report``、``sentry_handover``、``duty_info``、``duty_manage`` 或 ``acs_record``。
        不确定时可留空，由服务端结合会话上下文推断；仍歧义则 HITL 选择。
    start_time / end_time : str
        相对或绝对时间；未明确时可留空，由 HITL 补选。
    status / device_code / device_name : str
        仅 alarm_report 使用。
    sentry_id : str
        仅 sentry_handover 可选岗哨筛选。
    person_id : str
        仅 acs_record 可选人员筛选。

    返回（ToolResult JSON）
    ----------------------
    单文件：client_action={action:download, url, filename}；
    告警超量分批：client_actions 列表。拒绝导出时 user_cancelled=True。

    LLM 必须立即调用本工具，禁止先用自然语言追问时间。
    """
    resource_key = str(resource or "").strip()
    if resource_key and resource_key not in SUPPORTED_EXPORT_RESOURCES:
        supported = "、".join(sorted(SUPPORTED_EXPORT_RESOURCES))
        return tool_result(
            ok=False,
            summary=f"暂不支持导出类型「{resource_key}」，当前支持：{supported}。",
        )

    from contracts.context import current_turn_suppressed_tools

    if "download_file" in (current_turn_suppressed_tools.get() or frozenset()):
        return tool_result(
            ok=False,
            summary="上一轮导出已取消，本轮为新的导航请求，请勿重复导出。",
        )

    from contracts.tool_preflight import ensure_tool_args

    try:
        params = ensure_tool_args(
            "download_file",
            {
                "resource": resource_key,
                "start_time": start_time,
                "end_time": end_time,
                "status": status,
                "device_code": device_code,
                "device_name": device_name,
                "sentry_id": sentry_id,
                "person_id": person_id,
            },
        )
    except ValueError as exc:
        return tool_result(ok=False, summary=str(exc))

    resource_key = str(params.get("resource") or "").strip()
    if resource_key not in SUPPORTED_EXPORT_RESOURCES:
        supported = "、".join(sorted(SUPPORTED_EXPORT_RESOURCES))
        return tool_result(
            ok=False,
            summary=f"暂不支持导出类型「{resource_key}」，当前支持：{supported}。",
        )

    start_time = str(params.get("start_time", start_time))
    end_time = str(params.get("end_time", end_time))

    if resource_key == "sentry_handover":
        return execute_sentry_handover_export(
            start_time=start_time,
            end_time=end_time,
            sentry_id=str(params.get("sentry_id") or sentry_id),
            require_confirm=True,
        )

    if resource_key == "duty_info":
        return execute_duty_info_export(
            start_time=start_time,
            end_time=end_time,
            require_confirm=True,
        )

    if resource_key == "duty_manage":
        return execute_duty_manage_export(
            start_time=start_time,
            end_time=end_time,
            require_confirm=True,
        )

    if resource_key == "acs_record":
        return execute_acs_record_export(
            start_time=start_time,
            end_time=end_time,
            person_id=str(params.get("person_id") or person_id),
            require_confirm=True,
        )

    from platform_mcp.runtime.tools.alarm import resolve_alarm_device_filter

    status_raw = params.get("status")
    if status_raw is None or status_raw == "" or status_raw == []:
        status_raw = status
    filter_params: dict[str, Any] = dict(params)
    if status_raw not in (None, "", []):
        filter_params["status"] = status_raw

    _codes, device_err = resolve_alarm_device_filter(
        filter_params,
        device_code=str(params.get("device_code") or device_code),
        device_name=str(params.get("device_name") or device_name),
        hitl_tool="download_file",
    )
    if device_err:
        return tool_result(ok=False, summary=device_err)

    return execute_alarm_export(
        start_time=start_time,
        end_time=end_time,
        status=status_raw if status_raw not in (None, "") else "",
        filter_params=filter_params,
        require_confirm=True,
    )
