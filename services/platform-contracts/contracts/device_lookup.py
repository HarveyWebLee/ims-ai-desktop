"""设备编码/变量解析与列表请求体构造（供 preflight / resolver / tools 共用）。"""

from __future__ import annotations

import re
import uuid
from typing import Any

from contracts.hitl import ask_user_params
from contracts.platform_client import PlatformApiError, call_platform_api

QUERY_DEVICE_PAGE_SIZE = 20

_ONLINE_STATUS_MAP: dict[str, int] = {
    "在线": 1,
    "online": 1,
    "离线": 0,
    "offline": 0,
    "异常": 2,
    "abnormal": 2,
}

_ONLINE_STATUS_LABELS: dict[int, str] = {
    0: "离线",
    1: "在线",
    2: "异常",
}


def normalize_name_token(text: str) -> str:
    """变量名/showName 比较前归一化：去首尾空白、合并连续空白。"""
    return re.sub(r"\s+", "", (text or "").strip())


def looks_like_show_name(text: str) -> bool:
    """启发式：含 CJK 字符时优先用 showName 走平台服务端筛选。"""
    for ch in text:
        if "\u4e00" <= ch <= "\u9fff":
            return True
    return False


def map_online_status_token(value: str) -> int | None:
    """将 LLM 传入的在线状态口语映射为平台整型码。"""
    text = (value or "").strip()
    if not text:
        return None
    if text.isdigit():
        code = int(text)
        return code if code in _ONLINE_STATUS_LABELS else None
    return _ONLINE_STATUS_MAP.get(text) or _ONLINE_STATUS_MAP.get(text.lower())


def extract_device_records(data: Any) -> tuple[int, list[dict[str, Any]]]:
    """从平台分页响应提取 total 与 records。"""
    if isinstance(data, dict):
        records = data.get("records") or data.get("list") or data.get("rows") or []
        total = int(data.get("total") or data.get("totalCount") or len(records))
    elif isinstance(data, list):
        records = data
        total = len(records)
    else:
        records = []
        total = 0
    return total, [item for item in records if isinstance(item, dict)]


def extract_variable_records(data: Any) -> list[dict[str, Any]]:
    """从 getVarListByCode 响应提取变量列表。"""
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        records = data.get("records") or data.get("list") or data.get("rows") or []
        if isinstance(records, list):
            return [item for item in records if isinstance(item, dict)]
    return []


def build_var_list_request(device_code: str, keyword: str = "") -> dict[str, Any]:
    """构造 getVarListByCode 请求体（对齐 Swagger CreateDeviceGetVarListByCodeRequest）。"""
    payload: dict[str, Any] = {"deviceCode": device_code}
    kw = (keyword or "").strip()
    if kw:
        if looks_like_show_name(kw):
            payload["showName"] = kw
        else:
            payload["varName"] = kw
    return payload


def build_send_cmd_payload(
    *,
    device_code: str,
    var_name: str,
    variable_value: Any,
    operate_name: str,
) -> dict[str, Any]:
    """
    构造 sendCmd 请求体（对齐 Swagger + 平台前端 CommonController.sendCmd）。

    vs[].vv 强制 string；附带 willPostTs、taskNo 便于平台追踪。
    """
    vv_str = str(variable_value).strip()
    return {
        "dn": device_code,
        "operateName": operate_name,
        "vs": [{"vn": var_name, "vv": vv_str}],
        "willPostTs": True,
        "taskNo": uuid.uuid4().hex,
    }


def filter_exact_label_match(
    records: list[dict[str, Any]],
    token: str,
) -> list[dict[str, Any]]:
    """按 varName / showName 精确匹配（归一化空白），过滤平台模糊筛选的噪声。"""
    token_norm = normalize_name_token(token)
    exact: list[dict[str, Any]] = []
    for item in records:
        vn = str(item.get("varName") or item.get("var_name") or "").strip()
        sn = str(item.get("showName") or item.get("show_name") or "").strip()
        if vn and (vn == token or normalize_name_token(vn) == token_norm):
            exact.append(item)
        elif sn and (sn == token or normalize_name_token(sn) == token_norm):
            exact.append(item)
    return exact


def fetch_device_variable_records(
    device_code: str,
    keyword: str = "",
) -> list[dict[str, Any]]:
    """
    拉取设备变量列表；有关键词时优先服务端 varName/showName 筛选，
    中文 showName 筛选无结果时回退全量列表再客户端过滤。
    """
    kw = (keyword or "").strip()
    try:
        data = call_platform_api(
            method="post",
            path="/device/getVarListByCode",
            data=build_var_list_request(device_code, kw),
        )
    except PlatformApiError:
        raise

    records = extract_variable_records(data)
    if kw and not records and looks_like_show_name(kw):
        data = call_platform_api(
            method="post",
            path="/device/getVarListByCode",
            data={"deviceCode": device_code},
        )
        records = extract_variable_records(data)
        token_norm = normalize_name_token(kw)
        records = [
            item
            for item in records
            if normalize_name_token(str(item.get("showName") or item.get("show_name") or ""))
            == token_norm
            or str(item.get("varName") or item.get("var_name") or "").strip() == kw
        ]
    return records


def resolve_writable_variable_name(
    device_code: str,
    variable_name: str,
) -> tuple[str | None, str | None]:
    """
    将 LLM/用户输入的变量名（可能是 showName 中文名）解析为平台 varName。

    优先走 getVarListByCode 做 showName→varName 映射；**不校验 isWrite**。
    列表未命中、接口失败或设备无变量列表时：直接采用用户输入的 token。
    仅在「同名多项歧义」时返回 error。
    """
    token = (variable_name or "").strip()
    if not token:
        return None, "变量名不能为空。"

    token_norm = normalize_name_token(token)

    def _var_name_of(item: dict[str, Any]) -> str:
        return str(item.get("varName") or item.get("var_name") or "").strip()

    def _show_name_of(item: dict[str, Any]) -> str:
        return str(item.get("showName") or item.get("show_name") or "").strip()

    def _unique_var_name(items: list[dict[str, Any]]) -> str | None:
        names: list[str] = []
        for item in items:
            vn = _var_name_of(item)
            if vn and vn not in names:
                names.append(vn)
        return names[0] if len(names) == 1 else None

    try:
        filtered = fetch_device_variable_records(device_code, token)
        if len(filtered) > 1:
            narrowed = filter_exact_label_match(filtered, token)
            if narrowed:
                filtered = narrowed
        if filtered:
            unique = _unique_var_name(filtered)
            if unique:
                return unique, None
            if len({_var_name_of(i) for i in filtered if _var_name_of(i)}) > 1:
                labels = "、".join(
                    f"{_show_name_of(i) or _var_name_of(i)}({_var_name_of(i)})"
                    for i in filtered[:5]
                    if _var_name_of(i)
                )
                if labels:
                    return None, f"变量「{token}」匹配到多项：{labels}，请指定 varName。"

        records = fetch_device_variable_records(device_code)
    except PlatformApiError:
        return token, None

    exact_var: list[dict[str, Any]] = []
    exact_show: list[dict[str, Any]] = []
    for item in records or []:
        vn = _var_name_of(item)
        sn = _show_name_of(item)
        if vn and (normalize_name_token(vn) == token_norm or vn == token):
            exact_var.append(item)
        elif sn and (normalize_name_token(sn) == token_norm or sn == token):
            exact_show.append(item)

    unique = _unique_var_name(exact_var) or _unique_var_name(exact_show)
    if unique:
        return unique, None

    if len(exact_show) > 1:
        labels = "、".join(
            f"{_show_name_of(i) or _var_name_of(i)}({_var_name_of(i)})"
            for i in exact_show[:5]
            if _var_name_of(i)
        )
        return None, f"变量「{token}」对应多个 showName：{labels}，请指定 varName。"

    return token, None


def build_device_list_payload(
    *,
    search: str = "",
    device_name: str = "",
    device_code: str = "",
    online_status: int | None = None,
    page: int = 1,
    size: int = QUERY_DEVICE_PAGE_SIZE,
) -> dict[str, Any]:
    """
    构造 POST /device/getDeviceList 请求体。

    仅填入非空筛选字段，避免把空串带给平台造成误过滤。
    """
    payload: dict[str, Any] = {"page": page, "size": size}
    if search.strip():
        payload["search"] = search.strip()
    if device_name.strip():
        payload["deviceName"] = device_name.strip()
    if device_code.strip():
        payload["deviceCode"] = device_code.strip()
    if online_status is not None:
        payload["onlineStatus"] = online_status
    return payload


def resolve_device_code(
    device_code: str = "",
    device_name: str = "",
    *,
    hitl_tool: str = "get_device_detail",
) -> tuple[str | None, dict[str, Any] | None, str | None]:
    """
    解析设备编码：优先 device_code；仅有名称时查列表取首条或 HITL 消歧。
    返回 (device_code, device_record, error_message)。

    hitl_tool：多台设备需消歧时，ask_user_params 挂靠的工具名。
    """
    code = (device_code or "").strip()
    name = (device_name or "").strip()

    if code:
        try:
            data = call_platform_api(
                method="get",
                path=f"/device/getDeviceByCode/{code}",
            )
        except PlatformApiError as exc:
            return None, None, str(exc)
        if isinstance(data, dict) and data.get("deviceCode"):
            return str(data["deviceCode"]), data, None
        return None, None, f"未找到编码为「{code}」的设备。"

    if not name:
        return None, None, "请提供设备编码或设备名称。"

    payload = build_device_list_payload(device_name=name, size=10)
    try:
        data = call_platform_api(
            method="post",
            path="/device/getDeviceList",
            data=payload,
        )
    except PlatformApiError as exc:
        return None, None, str(exc)

    _, records = extract_device_records(data)
    if not records:
        return None, None, f"未找到名称含「{name}」的设备。"

    if len(records) == 1:
        item = records[0]
        return str(item.get("deviceCode") or ""), item, None

    options = [
        {
            "label": f"{item.get('deviceName', '-')} ({item.get('deviceCode', '-')})",
            "value": str(item.get("deviceCode") or ""),
        }
        for item in records[:10]
        if item.get("deviceCode")
    ]
    if not options:
        return None, None, f"找到 {len(records)} 台设备，但缺少有效编码。"

    merged = ask_user_params(
        tool=hitl_tool,
        message=f"找到 {len(records)} 台与「{name}」匹配的设备，请选择目标：",
        fields=[
            {
                "name": "device_code",
                "label": "目标设备",
                "type": "select",
                "required": True,
                "options": options,
            }
        ],
        current={},
    )
    selected = str(merged.get("device_code") or "").strip()
    if not selected:
        return None, None, "未选择目标设备。"
    matched = next((r for r in records if str(r.get("deviceCode")) == selected), None)
    if matched:
        return selected, matched, None
    return resolve_device_code(device_code=selected, hitl_tool=hitl_tool)
