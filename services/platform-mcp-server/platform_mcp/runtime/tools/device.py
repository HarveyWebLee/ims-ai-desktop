"""
设备相关 Server Tools 模块

文件职责
--------
向 LLM 暴露设备列表 / 详情 / 变量查询 / 指令下发；
经 ``platform_client`` 调用平台 ``/device/*``，统一 ``tool_result`` 返回。

白话概念
--------
值班员说「查一下空调在不在线」「帮我开下某某门禁」时走本模块。
查设备是只读；``send_device_cmd`` 会往设备写值，属于高风险，必须 HITL 确认。

在 Agent 流程中的位置
--------------------
  LLM / Plan 选中工具
    → ensure_tool_args / device_command_resolver（口语→编码/变量）
    → 本模块 @tool
    → call_platform_api → ToolResult

对外工具与平台 API
------------------
| 工具 | 主要平台 API | HITL 何时触发 | ToolResult 要点 |
| ---- | ------------ | ------------- | --------------- |
| query_devices | POST getDeviceList | 一般无（参数非法直接失败） | total/items/queryContext |
| get_device_detail | GET getDeviceByCode/{code}；名称歧义时 getDeviceList | 多名匹配 → ask_user_params 选设备 | data.device（脱敏） |
| query_device_variables | POST getVarListByCode；名称检索时 getDeviceList | 缺编码/名称 → preflight；多名匹配 → ask_user_params | items 变量摘要 |
| query_device_variable_realtime | POST getRealDataList（可联 getVarListByCode） | 缺设备 → HITL；变量可选（空=全部） | data.items[] 实时列表 |
| query_device_variable_history | POST getDevVarDataList | 缺设备/变量/时间 → HITL | 摘要点 + navigate |
| send_device_cmd | GET 设备详情 + POST sendCmd | 缺参 ask_params；写前 ask_user_confirm（含 device_preview）；开门/关门硬绑定 status_door_control、播报硬绑定 play 且失败不换变量；播报缺正文 HITL；其它动作失败可自动换变量重试一次（无需二次确认） | taskNo / auto_retry / 平台错误详情 |
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import tool

from contracts.device_lookup import (
    build_device_list_payload,
    build_send_cmd_payload,
    build_var_list_request,
    extract_device_records,
    extract_variable_records,
    fetch_device_variable_records,
    filter_exact_label_match,
    looks_like_show_name,
    map_online_status_token,
    normalize_name_token,
    resolve_device_code,
    resolve_writable_variable_name,
)
from contracts.hitl import ask_user_confirm, ask_user_params
from contracts.platform_client import PlatformApiError, call_platform_api
from contracts.result import tool_result

# 本地别名：保留既有私有名，避免大范围改 handler 内部调用
_normalize_name_token = normalize_name_token
_looks_like_show_name = looks_like_show_name
_map_online_status_token = map_online_status_token
_extract_device_records = extract_device_records
_extract_variable_records = extract_variable_records
_build_var_list_request = build_var_list_request
_build_send_cmd_payload = build_send_cmd_payload
_filter_exact_label_match = filter_exact_label_match
_fetch_device_variable_records = fetch_device_variable_records
_resolve_writable_variable_name = resolve_writable_variable_name
_resolve_device_code = resolve_device_code

# 返回给 LLM 的摘要条数上限
QUERY_DEVICE_PAGE_SIZE = 20
QUERY_DEVICE_VAR_PAGE_SIZE = 30

# 设备管理页 originPath（与 navigation_routes.json 对齐）
DEVICE_MANAGE_PATH = "/config_management/config/equipment_manage"


_ONLINE_STATUS_LABELS: dict[int, str] = {
    0: "离线",
    1: "在线",
    2: "异常",
}

# 平台 deviceStatus = 启用状态（与设备管理页一致：0 停用 / 1 启用）
_DEVICE_ENABLE_STATUS_LABELS: dict[int, str] = {
    0: "停用",
    1: "启用",
}

# 详情响应中需脱敏的字段
_SENSITIVE_DEVICE_KEYS = frozenset({"password", "userName"})


def _coerce_status_int(value: Any) -> int | None:
    """将平台状态字段规范为 int；无法解析时返回 None。"""
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value.strip())
    return None


def _map_enable_status(item: dict[str, Any]) -> tuple[int | None, str | None]:
    """
    解析启用状态码与中文标签。

    平台主字段为 deviceStatus；少数接口可能另带 enableStatus，二者择一。
    """
    code = _coerce_status_int(item.get("deviceStatus"))
    if code is None:
        code = _coerce_status_int(item.get("enableStatus"))
    label = _DEVICE_ENABLE_STATUS_LABELS.get(code) if code is not None else None
    return code, label


def _map_device_brief(item: dict[str, Any]) -> dict[str, Any]:
    """精简设备字段，供 LLM 与 Workspace 摘要展示。"""
    online = _coerce_status_int(item.get("onlineStatus"))
    online_label = _ONLINE_STATUS_LABELS.get(online) if online is not None else None
    enable_code, enable_label = _map_enable_status(item)
    return {
        "deviceCode": item.get("deviceCode"),
        "deviceName": item.get("deviceName"),
        "onlineStatus": online,
        "onlineStatusLabel": online_label,
        # deviceStatus 语义为启用状态；附带可读标签，避免 Workspace 展示原始码
        "deviceStatus": enable_code,
        "deviceStatusLabel": enable_label,
        "enableStatus": enable_code,
        "enableStatusLabel": enable_label,
        "regionName": item.get("regionName") or item.get("regionFullName"),
        "subSystemName": item.get("subSystemName"),
    }


def _map_device_detail(item: dict[str, Any]) -> dict[str, Any]:
    """设备详情字段映射（脱敏后供 LLM / Workspace）。"""
    brief = _map_device_brief(item)
    detail = {
        **brief,
        "id": item.get("id"),
        "ipAddress": item.get("ipAddress"),
        "port": item.get("port"),
        "manufacturer": item.get("manufacturer"),
        "model": item.get("model"),
        "location": item.get("location"),
        "deviceGroupName": item.get("deviceGroupName"),
        "collectServerName": item.get("collectServerName"),
        "commDeviceName": item.get("commDeviceName"),
        "firstUseTime": item.get("firstUseTime"),
    }
    for key in _SENSITIVE_DEVICE_KEYS:
        if key in item and item.get(key):
            detail[key] = "***"
    return detail


def _map_variable_brief(item: dict[str, Any]) -> dict[str, Any]:
    """精简设备变量字段。"""
    return {
        "varName": item.get("varName") or item.get("var_name"),
        "showName": item.get("showName") or item.get("show_name"),
        "varAddress": item.get("varAddress") or item.get("var_address"),
        "isRead": item.get("isRead"),
        "isWrite": item.get("isWrite"),
        "dataTypeName": item.get("dataTypeName") or item.get("valueTypeName"),
    }


def _is_writable_variable(item: dict[str, Any]) -> bool:
    """判断变量是否可写（平台 isWrite：1/true 为可写）。供展示/摘要用，下发不再据此拦截。"""
    iw = item.get("isWrite")
    if iw is None:
        return True
    if isinstance(iw, bool):
        return iw
    if isinstance(iw, (int, float)):
        return int(iw) == 1
    text = str(iw).strip().lower()
    return text in ("1", "true", "yes")


def _check_device_cmd_preconditions(device_record: dict[str, Any]) -> str | None:
    """
    下发前校验设备启用状态；返回 None 表示通过，否则为可读错误说明。

    离线设备不拦截：允许 confirm 后下发，平台 API 异常时由调用方返回错误摘要。
    """
    name = str(device_record.get("deviceName") or device_record.get("deviceCode") or "")
    # 平台启用态以 deviceStatus 为准（enableStatus 多为别名或缺失）
    enable_code, _ = _map_enable_status(device_record)
    if enable_code == 0:
        return f"设备「{name}」已停用，无法下发指令。请先在设备管理中启用设备。"
    return None


def _stringify_platform_error_data(data: Any) -> str:
    """将平台 API 错误 data 字段转为可读字符串（原样保留结构）。"""
    if data is None:
        return ""
    if isinstance(data, str):
        return data.strip()
    try:
        return json.dumps(data, ensure_ascii=False, indent=2)
    except TypeError, ValueError:
        return str(data)


def _classify_send_cmd_platform_error(exc: PlatformApiError) -> str:
    """
    分类 sendCmd 平台错误，用于决定是否换变量重试及摘要文案。

    - driver_timeout：驱动/网关超时（换 varName 无意义）
    - variable_or_unknown：变量/参数类或未知，可尝试备选变量
    """
    detail = _stringify_platform_error_data(exc.data).lower()
    combined = f"{exc} {detail}".lower()
    driver_markers = (
        "驱动服务",
        "驱动",
        "超时未响应",
        "超时",
        "timeout",
        "未响应",
        "通信失败",
        "连接失败",
        "offline",
        "离线",
    )
    if any(m.lower() in combined for m in driver_markers):
        return "driver_timeout"
    return "variable_or_unknown"


def _format_send_cmd_platform_error(
    exc: PlatformApiError,
    *,
    device_code: str,
    var_name: str,
) -> str:
    """将平台 sendCmd 异常转为可操作的中文摘要（含 data 原样详情）。"""
    raw = str(exc).strip() or "平台 API 调用失败"
    detail = _stringify_platform_error_data(exc.data)
    kind = _classify_send_cmd_platform_error(exc)

    if kind == "driver_timeout":
        core = detail or raw
        code_suffix = f"（业务码 {exc.code}）" if exc.code is not None else ""
        return (
            f"设备「{device_code}」指令已提交至平台，但驱动/网关未在规定时间内响应：{core}{code_suffix}。"
            "这通常与变量名无关，请检查：门禁驱动服务是否运行、设备是否在线、"
            "驱动与设备通信是否正常；必要时在平台设备管理中重试或联系运维。"
        )

    if raw in ("发生错误", "平台 API 调用失败") or not raw:
        return (
            f"设备「{device_code}」指令下发失败：{detail or raw}。"
            f"请确认 varName「{var_name}」存在、设备已启用并在线；"
            "可使用 query_device_variables 核对变量列表。"
        )

    parts = [raw]
    if exc.code is not None:
        parts.append(f"（业务码 {exc.code}）")
    if detail and detail != raw:
        parts.append(f"详情：{detail}")
    return "".join(parts)


def _build_platform_error_data(
    exc: PlatformApiError,
    *,
    request_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """构造 tool_result.data 中的平台错误详情（原样透传 platform_data）。"""
    out: dict[str, Any] = {
        "platform_code": exc.code,
        "platform_message": str(exc),
        "platform_data": exc.data,
        "failure_kind": _classify_send_cmd_platform_error(exc),
    }
    if request_payload:
        out["request"] = request_payload
    return out


def _post_send_cmd(
    payload: dict[str, Any],
) -> None:
    """调用平台 sendCmd；失败时抛出 PlatformApiError。"""
    call_platform_api(
        method="post",
        path="/device/sendCmd",
        data=payload,
    )


def _send_cmd_with_auto_retry(
    *,
    device_code: str,
    device_name: str,
    var_name: str,
    var_input: str,
    variable_value: str,
    operate_name: str,
    action: str,
    payload: dict[str, Any],
) -> str:
    """
    下发设备指令；失败时若可推断备选变量则底层自动重试一次（无需二次 HITL）。
    """
    from contracts.agent_debug import agent_debug
    from contracts.device_command_resolver import pick_alternate_writable_variable

    try:
        _post_send_cmd(payload)
        return tool_result(
            ok=True,
            summary=f"已成功向设备「{device_name}」（{device_code}）下发变量 {var_name}={variable_value}。",
            data={
                "deviceCode": device_code,
                "deviceName": device_name,
                "variableName": var_name,
                "variableValue": variable_value,
                "taskNo": payload.get("taskNo"),
            },
        )
    except PlatformApiError as exc:
        first_error = _build_platform_error_data(exc, request_payload=payload)
        failure_kind = first_error.get("failure_kind")
        alt_vn, alt_label = (None, None)
        # 驱动/网关超时：换 varName 无法解决，不自动重试
        if failure_kind != "driver_timeout":
            alt_vn, alt_label = pick_alternate_writable_variable(
                device_code,
                exclude_var=var_name,
                action=action,
            )
        if alt_vn and alt_vn != var_name:
            retry_payload = _build_send_cmd_payload(
                device_code=device_code,
                var_name=alt_vn,
                variable_value=variable_value,
                operate_name=operate_name,
            )
            agent_debug(
                "flow.device.send_cmd_auto_retry",
                device_code=device_code,
                from_var=var_name,
                to_var=alt_vn,
                action=action or None,
            )
            try:
                _post_send_cmd(retry_payload)
                return tool_result(
                    ok=True,
                    summary=(
                        f"变量「{var_input or var_name}」下发失败，"
                        f"已自动改用「{alt_label or alt_vn}」重试并成功。"
                    ),
                    data={
                        "deviceCode": device_code,
                        "deviceName": device_name,
                        "variableName": alt_vn,
                        "variableValue": variable_value,
                        "taskNo": retry_payload.get("taskNo"),
                        "auto_retry": {"from": var_name, "to": alt_vn},
                        "first_error": first_error,
                    },
                )
            except PlatformApiError as retry_exc:
                first_error["auto_retry"] = {"from": var_name, "to": alt_vn}
                first_error["retry_error"] = _build_platform_error_data(
                    retry_exc,
                    request_payload=retry_payload,
                )
                summary = _format_send_cmd_platform_error(
                    retry_exc,
                    device_code=device_code,
                    var_name=alt_vn,
                )
                return tool_result(
                    ok=False,
                    summary=(
                        f"变量「{var_input or var_name}」下发失败，"
                        f"已自动改用「{alt_label or alt_vn}」重试仍失败。"
                        f"{summary}"
                    ),
                    data=first_error,
                )

        summary = _format_send_cmd_platform_error(
            exc,
            device_code=device_code,
            var_name=var_name,
        )
        return tool_result(ok=False, summary=summary, data=first_error)


def _build_send_cmd_confirm_message(
    *,
    device_code: str,
    device_name: str,
    variable_name: str,
    variable_value: str,
    operate_name: str,
) -> str:
    """构造设备指令下发前的 HITL 确认文案。"""
    display = device_name or device_code
    op = operate_name.strip() or "设备控制指令"
    return (
        f"即将向设备「{display}」（{device_code}）下发指令：\n"
        f"- 操作：{op}\n"
        f"- 变量：{variable_name}\n"
        f"- 写入值：{variable_value}\n\n"
        "此为高风险写操作，确认后将立即下发至设备，是否继续？"
    )


def _build_device_cmd_preview(
    *,
    device_record: dict[str, Any] | None,
    device_code: str,
    device_name: str,
    variable_name: str,
    variable_value: str,
    operate_name: str,
) -> dict[str, Any]:
    """构造 confirm interrupt 的 device_preview（前端同屏展示）。"""
    detail = _map_device_detail(device_record) if device_record else {}
    return {
        "deviceCode": detail.get("deviceCode") or device_code,
        "deviceName": detail.get("deviceName") or device_name or device_code,
        "onlineStatusLabel": detail.get("onlineStatusLabel"),
        "regionName": detail.get("regionName"),
        "subSystemName": detail.get("subSystemName"),
        "variableName": variable_name,
        "variableValue": variable_value,
        "operateName": operate_name.strip() or "设备控制指令",
    }


def _resolve_variable_on_device(
    device_code: str,
    variable_name: str,
) -> tuple[str, str, dict[str, Any] | None, str | None]:
    """
    在设备上解析变量名 → (varName, showName, record, error)。
    无匹配或歧义时返回 error 文案。
    """
    kw = (variable_name or "").strip()
    if not kw:
        return "", "", None, "请指定变量名（varName 或中文显示名）。"
    try:
        records = _fetch_device_variable_records(device_code, kw)
    except PlatformApiError as exc:
        return "", "", None, str(exc)
    exact = _filter_exact_label_match(records, kw) if records else []
    candidates = exact or records
    if not candidates:
        return "", "", None, f"设备「{device_code}」上未找到变量「{kw}」。"
    if len(candidates) > 1:
        labels = []
        for item in candidates[:8]:
            vn = str(item.get("varName") or "").strip()
            sn = str(item.get("showName") or "").strip()
            labels.append(f"{sn or vn}（{vn}）" if sn and sn != vn else vn)
        return (
            "",
            "",
            None,
            "找到多个匹配变量，请改用精确 varName：" + "、".join(labels),
        )
    item = candidates[0]
    vn = str(item.get("varName") or item.get("var_name") or "").strip()
    sn = str(item.get("showName") or item.get("show_name") or "").strip()
    if not vn:
        return "", "", None, f"变量「{kw}」缺少 varName，无法查询。"
    return vn, sn, item, None


HISTORY_CURVE_PATH = "/config_management/config/history_statistics"

# 口语「全部变量」关键词：命中则按设备拉全量实时列表
_ALL_VARIABLES_TOKENS = frozenset(
    {
        "",
        "*",
        "all",
        "全部",
        "所有",
        "全量",
        "所有变量",
        "全部变量",
        "所有变量实时值",
        "全部变量实时值",
    }
)


def _is_all_variables_request(variable_name: str) -> bool:
    """判断是否查询设备下全部变量实时值。"""
    token = _normalize_name_token(variable_name or "")
    if not token:
        return True
    lower = token.lower()
    if lower in _ALL_VARIABLES_TOKENS or token in _ALL_VARIABLES_TOKENS:
        return True
    # 「所有xxx实时」「全部变量」等宽松匹配
    return ("全部" in token or "所有" in token) and (
        "变量" in token or "实时" in token or lower == "all"
    )


def _extract_list_records(data: Any) -> list[dict[str, Any]]:
    """从平台列表响应提取 dict 行。"""
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    if isinstance(data, dict):
        raw = data.get("list") or data.get("records") or data.get("items") or []
        if isinstance(raw, list):
            return [r for r in raw if isinstance(r, dict)]
    return []


def _map_realtime_item(
    *,
    var_name: str,
    show_name: str,
    row: dict[str, Any] | None,
) -> dict[str, Any]:
    """将平台实时行映射为 Workspace / LLM 摘要条目。"""
    real = row.get("realData") if row and isinstance(row.get("realData"), dict) else {}
    value = real.get("vv") if real else (row.get("vv") if row else None)
    updated_at = real.get("now") if real else None
    quality = real.get("vt") if real else None
    unit = None
    if row:
        unit = row.get("unit") or row.get("unitName")
        sn = str(row.get("showName") or show_name or var_name).strip()
        vn = str(row.get("varName") or var_name).strip()
    else:
        sn = show_name or var_name
        vn = var_name
    return {
        "varName": vn,
        "showName": sn,
        "value": value,
        "unit": unit,
        "quality": quality,
        "updated_at": updated_at,
        "has_value": value is not None and str(value).strip() != "",
    }


def _fetch_realtime_rows(device_code: str, var_name: str = "") -> list[dict[str, Any]]:
    """调用 getRealDataList；可选按 varName 过滤。"""
    payload: dict[str, Any] = {
        "page": 1,
        "size": 200,
        "deviceCode": device_code,
    }
    if var_name:
        payload["varName"] = var_name
    data = call_platform_api(
        method="post",
        path="/realData/getRealDataList",
        data=payload,
    )
    return _extract_list_records(data)


@tool
def query_device_variable_realtime(
    device_code: str = "",
    device_name: str = "",
    variable_name: str = "",
) -> str:
    """
    帮使用者查询指定设备变量的实时当前值（只读）。

    variable_name 留空或「所有/全部」时返回该设备全部变量实时列表。
    平台 API：POST ``/realData/getRealDataList``；变量清单联 ``getVarListByCode``。
    """
    from contracts.tool_preflight import ensure_tool_args

    try:
        merged = ensure_tool_args(
            "query_device_variable_realtime",
            {
                "device_code": device_code,
                "device_name": device_name,
                "variable_name": variable_name,
            },
        )
    except ValueError as exc:
        return tool_result(ok=False, summary=str(exc))

    code, device_record, error = _resolve_device_code(
        device_code=str(merged.get("device_code") or ""),
        device_name=str(merged.get("device_name") or ""),
        hitl_tool="query_device_variable_realtime",
    )
    if error:
        return tool_result(ok=False, summary=error)
    if not code:
        return tool_result(ok=False, summary="未能解析目标设备编码。")

    device_label = code
    if isinstance(device_record, dict):
        device_label = str(device_record.get("deviceName") or code)
    else:
        try:
            detail = call_platform_api(
                method="get",
                path=f"/device/getDeviceByCode/{code}",
            )
            if isinstance(detail, dict):
                device_label = str(detail.get("deviceName") or code)
        except PlatformApiError:
            pass

    var_raw = str(merged.get("variable_name") or "").strip()
    query_all = _is_all_variables_request(var_raw)

    # 变量清单（保证「全部」时即使实时接口无行也能列出配置变量）
    try:
        catalog_vars = _fetch_device_variable_records(code, "" if query_all else var_raw)
    except PlatformApiError as exc:
        return tool_result(ok=False, summary=str(exc))

    filter_vn = ""
    filter_sn = ""
    if not query_all:
        vn, sn, _var_rec, var_err = _resolve_variable_on_device(code, var_raw)
        if var_err:
            return tool_result(ok=False, summary=var_err)
        filter_vn, filter_sn = vn, sn
        if not catalog_vars and _var_rec:
            catalog_vars = [_var_rec]

    try:
        realtime_rows = _fetch_realtime_rows(code, filter_vn if not query_all else "")
    except PlatformApiError as exc:
        return tool_result(ok=False, summary=str(exc))

    # varName → 实时行（优先精确匹配）
    realtime_by_vn: dict[str, dict[str, Any]] = {}
    for row in realtime_rows:
        vn_key = str(row.get("varName") or "").strip()
        if not vn_key:
            continue
        if vn_key not in realtime_by_vn:
            realtime_by_vn[vn_key] = row

    items: list[dict[str, Any]] = []
    if catalog_vars:
        seen: set[str] = set()
        for var in catalog_vars:
            vn = str(var.get("varName") or var.get("var_name") or "").strip()
            if not vn or vn in seen:
                continue
            if not query_all and filter_vn and vn != filter_vn:
                continue
            seen.add(vn)
            sn = str(var.get("showName") or var.get("show_name") or "").strip()
            items.append(
                _map_realtime_item(
                    var_name=vn,
                    show_name=sn,
                    row=realtime_by_vn.get(vn),
                )
            )
        # 实时接口多出的行也并入（清单未覆盖时）
        for vn_key, row in realtime_by_vn.items():
            if vn_key in seen:
                continue
            if not query_all and filter_vn and vn_key != filter_vn:
                continue
            items.append(
                _map_realtime_item(
                    var_name=vn_key,
                    show_name=str(row.get("showName") or ""),
                    row=row,
                )
            )
    else:
        # 无变量清单：直接用实时行
        for row in realtime_rows:
            vn = str(row.get("varName") or "").strip()
            if not vn:
                continue
            if not query_all and filter_vn and vn != filter_vn:
                continue
            items.append(
                _map_realtime_item(
                    var_name=vn,
                    show_name=str(row.get("showName") or ""),
                    row=row,
                )
            )

    if not items and not query_all and filter_vn:
        # 单变量：清单与实时皆空时仍返回一条空值占位，避免「查不到」误导
        items = [
            _map_realtime_item(
                var_name=filter_vn,
                show_name=filter_sn,
                row=None,
            )
        ]

    if not items:
        return tool_result(
            ok=False,
            summary=f"设备「{device_label}」（{code}）未查询到变量实时数据。",
        )

    with_value = sum(1 for it in items if it.get("has_value"))
    if query_all or len(items) > 1:
        summary = (
            f"设备「{device_label}」（{code}）共 {len(items)} 个变量实时值，"
            f"其中 {with_value} 个有采集数据"
            f"{'，其余暂无上报' if with_value < len(items) else ''}。"
        )
    else:
        only = items[0]
        val = only.get("value")
        summary = (
            f"设备「{device_label}」变量「{only.get('showName') or only.get('varName')}」"
            f"（{only.get('varName')}）当前值："
            f"{val if only.get('has_value') else '—（暂无上报）'}。"
        )

    first = items[0]
    return tool_result(
        ok=True,
        summary=summary,
        data={
            "device": {
                "deviceCode": code,
                "deviceName": device_label,
            },
            # 兼容单变量卡片；多变量以 items 为准
            "variable": {
                "varName": first.get("varName"),
                "showName": first.get("showName"),
            },
            "value": first.get("value"),
            "unit": first.get("unit"),
            "quality": first.get("quality"),
            "updated_at": first.get("updated_at"),
            "total": len(items),
            "items": items,
            "scope": "all" if query_all or len(items) > 1 else "single",
        },
    )


@tool
def query_device_variable_history(
    device_code: str = "",
    device_name: str = "",
    variable_name: str = "",
    start_time: str = "",
    end_time: str = "",
) -> str:
    """
    帮使用者查询设备变量历史摘要，并提供跳转历史曲线页（只读）。

    平台 API：POST ``/sysMonitor/getDevVarDataList``。
    """
    from contracts.alarm_params import to_platform_time
    from contracts.time_range import resolve_alarm_time_range
    from contracts.tool_preflight import ensure_tool_args

    try:
        merged = ensure_tool_args(
            "query_device_variable_history",
            {
                "device_code": device_code,
                "device_name": device_name,
                "variable_name": variable_name,
                "start_time": start_time,
                "end_time": end_time,
            },
        )
    except ValueError as exc:
        return tool_result(ok=False, summary=str(exc))

    if not str(merged.get("variable_name") or "").strip():
        supplemented = ask_user_params(
            tool="query_device_variable_history",
            message="请补充要查询历史的变量名",
            fields=[
                {
                    "name": "variable_name",
                    "label": "变量名",
                    "type": "text",
                    "required": True,
                }
            ],
            current=merged,
        )
        merged = {**merged, **supplemented}

    code, _record, error = _resolve_device_code(
        device_code=str(merged.get("device_code") or ""),
        device_name=str(merged.get("device_name") or ""),
        hitl_tool="query_device_variable_history",
    )
    if error:
        return tool_result(ok=False, summary=error)
    if not code:
        return tool_result(ok=False, summary="未能解析目标设备编码。")

    vn, sn, _var_rec, var_err = _resolve_variable_on_device(
        code, str(merged.get("variable_name") or "")
    )
    if var_err:
        return tool_result(ok=False, summary=var_err)

    start_raw = str(merged.get("start_time") or "").strip()
    end_raw = str(merged.get("end_time") or "").strip()
    resolved = resolve_alarm_time_range(start_raw, end_raw)
    if not resolved:
        supplemented = ask_user_params(
            tool="query_device_variable_history",
            message="请选择历史数据的时间范围",
            fields=[
                {
                    "name": "time_range",
                    "label": "时间范围",
                    "type": "datetime_range",
                    "required": True,
                }
            ],
            current=merged,
        )
        merged = {**merged, **supplemented}
        start_raw = str(merged.get("start_time") or "").strip()
        end_raw = str(merged.get("end_time") or "").strip()
        resolved = resolve_alarm_time_range(start_raw, end_raw)
        if not resolved:
            return tool_result(ok=False, summary="时间范围无效，请重新选择。")

    start_iso, end_iso = resolved
    platform_start = to_platform_time(start_iso)
    platform_end = to_platform_time(end_iso)

    try:
        data = call_platform_api(
            method="post",
            path="/sysMonitor/getDevVarDataList",
            data={
                "startTime": platform_start,
                "endTime": platform_end,
                "page": 1,
                "size": 500,
                "devNoList": [
                    {
                        "devCode": code,
                        "deviceVarList": [{"varCode": vn}],
                    }
                ],
            },
        )
    except PlatformApiError as exc:
        return tool_result(ok=False, summary=str(exc))

    series: list[dict[str, Any]] = []
    if isinstance(data, list):
        series = [x for x in data if isinstance(x, dict)]
    elif isinstance(data, dict):
        raw = data.get("list") or data.get("records") or data.get("data") or []
        if isinstance(raw, list):
            series = [x for x in raw if isinstance(x, dict)]

    points: list[dict[str, Any]] = []
    for item in series:
        item_vn = str(item.get("vn") or item.get("varCode") or "").strip()
        if item_vn and item_vn != vn:
            continue
        device_data = item.get("deviceDataList") or item.get("dataList") or []
        if not isinstance(device_data, list):
            continue
        for pt in device_data:
            if not isinstance(pt, dict):
                continue
            points.append({"t": pt.get("ts"), "v": pt.get("val")})

    # 摘要：点数 + 首尾 + 数值 min/max（可解析时）
    numeric_vals: list[float] = []
    for p in points:
        try:
            numeric_vals.append(float(p["v"]))
        except TypeError, ValueError, KeyError:
            continue
    summary_bits = [f"共 {len(points)} 个测点"]
    if points:
        summary_bits.append(f"起 {points[0].get('v')} → 止 {points[-1].get('v')}")
    if numeric_vals:
        summary_bits.append(f"最小 {min(numeric_vals)} / 最大 {max(numeric_vals)}")
    device_label = ""
    var_label = sn or vn
    if series:
        device_label = str(series[0].get("devShowName") or series[0].get("dn") or "")
        var_label = str(series[0].get("varShowName") or var_label)

    summary = (
        f"设备「{device_label or code}」变量「{var_label}」（{vn}）"
        f"历史摘要：{'；'.join(summary_bits)}。"
        f"时间 {platform_start} ~ {platform_end}。"
    )
    # 侧栏表格只展示抽样点，完整曲线走页面跳转
    sample = points[:: max(1, len(points) // 20)][:20] if points else []
    return tool_result(
        ok=True,
        summary=summary,
        data={
            "device": {"deviceCode": code, "deviceName": device_label or code},
            "variable": {"varName": vn, "showName": var_label},
            "points": sample,
            "point_count": len(points),
            "summary": "；".join(summary_bits),
            "timeRange": {"start": platform_start, "end": platform_end},
            "navigate": {
                "path": HISTORY_CURVE_PATH,
                "query": {
                    "deviceCode": code,
                    "varName": vn,
                    "startTime": platform_start,
                    "endTime": platform_end,
                },
            },
        },
    )


@tool
def query_devices(
    search: str = "",
    device_name: str = "",
    device_code: str = "",
    online_status: str = "",
) -> str:
    """
    帮使用者查询设备列表（仅查询，不增删改）。

    参数
    ----
    search : str
        模糊关键词。
    device_name / device_code : str
        名称 / 编码筛选，可与 search 组合。
    online_status : str
        在线 / 离线 / 异常，或 0/1/2。

    平台 API
    --------
    POST ``/device/getDeviceList``。

    HITL
    ----
    一般不触发；在线状态非法直接 ok=False。

    返回（ToolResult JSON）
    ----------------------
    data.total / items（精简字段）/ queryContext（本次请求体）。
    """
    status_code = _map_online_status_token(online_status)
    if (online_status or "").strip() and status_code is None:
        return tool_result(
            ok=False,
            summary="在线状态无效，请使用：在线、离线、异常。",
        )

    payload = build_device_list_payload(
        search=search,
        device_name=device_name,
        device_code=device_code,
        online_status=status_code,
    )

    try:
        data = call_platform_api(
            method="post",
            path="/device/getDeviceList",
            data=payload,
        )
    except PlatformApiError as exc:
        return tool_result(ok=False, summary=str(exc))

    total, records = _extract_device_records(data)
    brief = [_map_device_brief(item) for item in records[:QUERY_DEVICE_PAGE_SIZE]]

    filter_parts: list[str] = []
    if search.strip():
        filter_parts.append(f"关键词「{search.strip()}」")
    if device_name.strip():
        filter_parts.append(f"名称「{device_name.strip()}」")
    if device_code.strip():
        filter_parts.append(f"编码「{device_code.strip()}」")
    if status_code is not None:
        filter_parts.append(f"状态「{_ONLINE_STATUS_LABELS.get(status_code, online_status)}」")
    scope = "，".join(filter_parts) if filter_parts else "全部设备"

    summary = f"共查询到 {total} 台设备（{scope}，展示前 {len(brief)} 条摘要）。"
    return tool_result(
        ok=True,
        summary=summary,
        data={
            "total": total,
            "items": brief,
            "page": 1,
            "pageSize": QUERY_DEVICE_PAGE_SIZE,
            "queryContext": payload,
        },
    )


@tool
def get_device_detail(device_code: str = "", device_name: str = "") -> str:
    """
    帮使用者查看单台设备详情。

    参数
    ----
    device_code / device_name : str
        至少一项；仅有名称时先列表匹配。

    平台 API
    --------
    GET ``/device/getDeviceByCode/{code}``；名称检索时另调 getDeviceList。

    HITL
    ----
    多名匹配 → ask_user_params 下拉选择 device_code；缺参走 preflight。

    返回（ToolResult JSON）
    ----------------------
    data.device：脱敏后的详情（password 等打码）。
    """
    from contracts.tool_preflight import ensure_tool_args

    try:
        merged = ensure_tool_args(
            "get_device_detail",
            {"device_code": device_code, "device_name": device_name},
        )
    except ValueError as exc:
        return tool_result(ok=False, summary=str(exc))

    code, record, error = _resolve_device_code(
        device_code=str(merged.get("device_code") or ""),
        device_name=str(merged.get("device_name") or ""),
    )
    if error:
        return tool_result(ok=False, summary=error)

    # 列表命中时已含详情字段；编码直查时 record 来自 getDeviceByCode
    if record is None and code:
        try:
            data = call_platform_api(
                method="get",
                path=f"/device/getDeviceByCode/{code}",
            )
            record = data if isinstance(data, dict) else None
        except PlatformApiError as exc:
            return tool_result(ok=False, summary=str(exc))

    if not record:
        return tool_result(ok=False, summary=f"未获取到设备「{code}」的详情。")

    detail = _map_device_detail(record)
    name = detail.get("deviceName") or code
    status = detail.get("onlineStatusLabel") or "未知"
    region = detail.get("regionName") or "-"
    summary = (
        f"设备「{name}」（{code}）：在线状态 {status}，"
        f"区域 {region}，子系统 {detail.get('subSystemName') or '-'}。"
    )
    return tool_result(
        ok=True,
        summary=summary,
        data={
            "device": detail,
            # BPMN 条件表达式可直接引用 steps.{nodeId}.onlineStatus
            "onlineStatus": status,
        },
    )


@tool
def query_device_variables(
    device_code: str = "",
    device_name: str = "",
    var_name: str = "",
) -> str:
    """
    帮使用者查询指定设备下的变量列表。

    参数
    ----
    device_code / device_name : str
        至少一项；仅有名称时先列表匹配（与 get_device_detail 对齐）。
    var_name : str
        可选；中文倾向按 showName、英文按 varName 做服务端筛选。

    平台 API
    --------
    POST ``/device/getVarListByCode``；名称检索时另调 getDeviceList。

    HITL
    ----
    缺参走 preflight（one_of）；多名匹配 → ask_user_params 下拉选择 device_code。

    返回（ToolResult JSON）
    ----------------------
    data.items：变量摘要（含 isRead/isWrite）；供后续 send_device_cmd 选可写变量。
    """
    from contracts.tool_preflight import ensure_tool_args

    try:
        merged = ensure_tool_args(
            "query_device_variables",
            {
                "device_code": device_code,
                "device_name": device_name,
                "var_name": var_name,
            },
        )
    except ValueError as exc:
        return tool_result(ok=False, summary=str(exc))

    code, _record, error = _resolve_device_code(
        device_code=str(merged.get("device_code") or ""),
        device_name=str(merged.get("device_name") or ""),
        hitl_tool="query_device_variables",
    )
    if error:
        return tool_result(ok=False, summary=error)
    if not code:
        return tool_result(ok=False, summary="未能解析目标设备编码。")

    keyword = str(merged.get("var_name") or "").strip()

    try:
        records = _fetch_device_variable_records(code, keyword)
    except PlatformApiError as exc:
        return tool_result(ok=False, summary=str(exc))

    brief = [_map_variable_brief(item) for item in records[:QUERY_DEVICE_VAR_PAGE_SIZE]]
    scope = f"设备 {code}"
    if keyword:
        scope += f"，变量关键词「{keyword}」"
    summary = f"共查询到 {len(records)} 个变量（{scope}，展示前 {len(brief)} 条）。"
    return tool_result(
        ok=True,
        summary=summary,
        data={
            "deviceCode": code,
            "total": len(records),
            "items": brief,
            "pageSize": QUERY_DEVICE_VAR_PAGE_SIZE,
        },
    )


@tool
def send_device_cmd(
    device_code: str = "",
    device_name: str = "",
    variable_name: str = "",
    variable_value: str = "",
    action: str = "",
    operate_name: str = "",
) -> str:
    """
    帮使用者向设备下发控制指令（高风险，执行前须 HITL 确认）。

    参数
    ----
    device_code / device_name : str
        目标设备；名称可由 Resolver / HITL 解析为编码。
    variable_name / variable_value : str
        写入变量名（可为 showName）与值。
    action : str
        口语动作（开门/关门/播报等）。开门/关门硬绑定 status_door_control；
        播报硬绑定 play，写入值为播报正文。
    operate_name : str
        平台操作名；空则默认「AI助手下发指令」。

    平台 API
    --------
    GET ``/device/getDeviceByCode/{code}``（校验/展示）→
    POST ``/device/sendCmd``（body：dn/vs/operateName/taskNo…）。

    HITL
    ----
    - 缺参：Resolver 给出 interrupt → ask_user_params
    - 写前：ask_user_confirm；拒绝则不调 sendCmd
    - 开门/关门无 status_door_control、播报无 play：直接失败，不弹变量选择、不换变量重试
    - 播报正文未明确：HITL 补填「播报内容」
    - 其它动作失败自动换备选变量重试一次时不再二次确认（防重复打扰）

    返回（ToolResult JSON）
    ----------------------
    成功含 taskNo；失败含 platform_code / failure_kind。
    """
    from contracts.device_command_resolver import resolve_device_command
    from contracts.tool_preflight import ensure_tool_args

    initial_args = {
        "device_code": device_code,
        "device_name": device_name,
        "variable_name": variable_name,
        "variable_value": variable_value,
        "action": action,
        "operate_name": operate_name,
    }

    try:
        merged = ensure_tool_args("send_device_cmd", initial_args)
    except ValueError as exc:
        return tool_result(ok=False, summary=str(exc))

    resolution = resolve_device_command(
        device_code=str(merged.get("device_code") or ""),
        device_name=str(merged.get("device_name") or ""),
        variable_name=str(merged.get("variable_name") or ""),
        variable_value=str(merged.get("variable_value") or ""),
        action=str(merged.get("action") or ""),
        operate_name=str(merged.get("operate_name") or ""),
        user_text=str(merged.get("action") or merged.get("variable_name") or ""),
    )

    if resolution.interrupt:
        interrupt_fields = list(resolution.interrupt.get("fields") or [])
        # fields 为空：硬失败（如门控无 status_door_control），不走 HITL
        if not interrupt_fields:
            return tool_result(
                ok=False,
                summary=str(resolution.interrupt.get("message") or "无法下发设备指令。"),
                data={"non_retryable": True, "failure_kind": "required_var_unsupported"},
            )
        supplemented = ask_user_params(
            tool="send_device_cmd",
            message=str(resolution.interrupt.get("message") or "请补充设备指令参数"),
            fields=interrupt_fields,
            current={**merged, **resolution.to_tool_args()},
        )
        merged = {**merged, **supplemented}
        # 用户已在 HITL 选定变量时，禁止 action 路径再次覆盖推断结果
        if str(supplemented.get("variable_name") or "").strip():
            merged["action"] = ""
        resolution = resolve_device_command(
            device_code=str(merged.get("device_code") or ""),
            device_name=str(merged.get("device_name") or ""),
            variable_name=str(merged.get("variable_name") or ""),
            variable_value=str(merged.get("variable_value") or ""),
            action=str(merged.get("action") or ""),
            operate_name=str(merged.get("operate_name") or ""),
            user_text=str(merged.get("action") or merged.get("variable_name") or ""),
        )
        if resolution.interrupt or not resolution.is_complete():
            # HITL 已给齐设备+变量+值：强制放行，本地不再因可写/存在性拦截
            force_dc = str(merged.get("device_code") or "").strip()
            force_vn = str(merged.get("variable_name") or "").strip()
            force_vv = str(merged.get("variable_value") or "").strip()
            if force_dc and force_vn and force_vv:
                from contracts.agent_debug import agent_debug

                agent_debug(
                    "flow.device.explicit_var_passthrough",
                    device_code=force_dc,
                    variable_name=force_vn,
                    had_interrupt=resolution.interrupt is not None,
                )
                resolution.device_code = resolution.device_code or force_dc
                resolution.variable_name = force_vn
                resolution.variable_input = force_vn
                resolution.variable_value = force_vv
                resolution.missing = []
                resolution.interrupt = None
            else:
                msg = str(
                    (resolution.interrupt or {}).get("message")
                    or "参数仍不完整，请指定设备、变量与写入值。"
                )
                interrupt_type = str((resolution.interrupt or {}).get("type") or "")
                non_retryable = interrupt_type == "error" or not list(
                    (resolution.interrupt or {}).get("fields") or []
                )
                data = {"non_retryable": True} if non_retryable else None
                return tool_result(ok=False, summary=msg, data=data)

    if not resolution.is_complete():
        # 调用方已显式给齐三要素时同样放行（resume 直传 / 无 HITL 二次解析）
        force_dc = str(merged.get("device_code") or resolution.device_code or "").strip()
        force_vn = str(merged.get("variable_name") or resolution.variable_name or "").strip()
        force_vv = str(merged.get("variable_value") or resolution.variable_value or "").strip()
        if force_dc and force_vn and force_vv:
            from contracts.agent_debug import agent_debug

            agent_debug(
                "flow.device.explicit_var_passthrough",
                device_code=force_dc,
                variable_name=force_vn,
                phase="pre_complete",
            )
            resolution.device_code = force_dc
            resolution.variable_name = force_vn
            resolution.variable_input = force_vn
            resolution.variable_value = force_vv
            resolution.missing = []
            resolution.interrupt = None
        else:
            return tool_result(ok=False, summary="缺少设备、变量或写入值，无法下发指令。")

    code = resolution.device_code or ""
    vn_input = resolution.variable_input or resolution.variable_name or ""
    vn = resolution.variable_name or ""
    vv_str = str(resolution.variable_value or "").strip()
    op_name = str(resolution.operate_name or merged.get("operate_name") or "").strip()
    if not op_name:
        op_name = "AI助手下发指令"

    # 拉取设备详情：确认文案 + 下发前状态校验
    device_name = code
    device_record: dict[str, Any] | None = None
    try:
        dev_data = call_platform_api(
            method="get",
            path=f"/device/getDeviceByCode/{code}",
        )
        if isinstance(dev_data, dict):
            device_record = dev_data
            device_name = str(dev_data.get("deviceName") or code)
    except PlatformApiError:
        device_name = code

    if device_record is not None:
        pre_err = _check_device_cmd_preconditions(device_record)
        if pre_err:
            return tool_result(ok=False, summary=pre_err)

    approved = ask_user_confirm(
        tool="send_device_cmd",
        message=_build_send_cmd_confirm_message(
            device_code=code,
            device_name=device_name,
            variable_name=vn if vn == vn_input else f"{vn_input} → {vn}",
            variable_value=vv_str,
            operate_name=op_name,
        ),
        device_preview=_build_device_cmd_preview(
            device_record=device_record,
            device_code=code,
            device_name=device_name,
            variable_name=vn if vn == vn_input else f"{vn_input} → {vn}",
            variable_value=vv_str,
            operate_name=op_name,
        ),
    )
    if not approved:
        return tool_result(ok=False, summary="使用者已取消设备指令下发。")

    payload = _build_send_cmd_payload(
        device_code=code,
        var_name=vn,
        variable_value=vv_str,
        operate_name=op_name,
    )

    from contracts.agent_debug import agent_debug, summarize_tool_args

    agent_debug(
        "flow.device.send_cmd",
        device_code=code,
        var_name=vn,
        var_input=vn_input if vn_input != vn else None,
        payload_summary=summarize_tool_args(payload),
    )

    return _send_cmd_with_auto_retry(
        device_code=code,
        device_name=device_name,
        var_name=vn,
        var_input=vn_input,
        variable_value=vv_str,
        operate_name=op_name,
        action=str(merged.get("action") or resolution.action or ""),
        payload=payload,
    )
