"""表行 → 向量化文本 / payload。"""

from __future__ import annotations

from typing import Any

# 设备向量 payload 白名单（与平台设备 API 字段对齐；不含 password）
_DEVICE_PAYLOAD_KEYS: tuple[str, ...] = (
    "id",
    "deviceName",
    "deviceCode",
    "subSystemId",
    "subSystemName",
    "deviceGroupId",
    "deviceGroupName",
    "commDeviceId",
    "commDeviceCode",
    "commDeviceName",
    "collectServerId",
    "collectServerName",
    "deviceCategoryId",
    "deviceCategoryName",
    "ipAddress",
    "userName",
    "location",
    "lngLat",
)

# 达梦列名（已小写）→ 平台 camelCase；含常见别名
_DEVICE_COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "id": ("id", "device_id", "deviceid"),
    "deviceName": ("device_name", "devicename", "name"),
    "deviceCode": ("device_code", "devicecode", "dn", "code"),
    "subSystemId": ("sub_system_id", "subsystemid", "subsystem_id"),
    "subSystemName": ("sub_system_name", "subsystemname", "subsystem_name"),
    "deviceGroupId": ("device_group_id", "devicegroupid"),
    "deviceGroupName": ("device_group_name", "devicegroupname"),
    "commDeviceId": ("comm_device_id", "commdeviceid"),
    "commDeviceCode": ("comm_device_code", "commdevicecode"),
    "commDeviceName": ("comm_device_name", "commdevicename"),
    "collectServerId": ("collect_server_id", "collectserverid"),
    "collectServerName": ("collect_server_name", "collectservername"),
    "deviceCategoryId": ("device_category_id", "devicecategoryid"),
    "deviceCategoryName": ("device_category_name", "devicecategoryname"),
    "ipAddress": ("ip_address", "ipaddress", "ip"),
    "userName": ("user_name", "username", "user"),
    "location": ("location", "addr", "address"),
    "lngLat": ("lng_lat", "lnglat", "lon_lat", "lat_lng"),
}

# 写入 embedding 正文的字段（中文标签）；不含账号类字段
_DEVICE_TEXT_LABELS: tuple[tuple[str, str], ...] = (
    ("deviceCode", "设备编码"),
    ("deviceName", "设备名称"),
    ("subSystemName", "子系统"),
    ("deviceGroupName", "设备分组"),
    ("commDeviceCode", "通信网关编码"),
    ("commDeviceName", "通信网关"),
    ("collectServerName", "数采服务"),
    ("deviceCategoryName", "设备类型"),
    ("ipAddress", "IP"),
    ("location", "位置"),
    ("lngLat", "经纬度"),
)


def _pick(row: dict[str, Any], *candidates: str) -> Any:
    """按候选列名（小写）取值。"""
    for key in candidates:
        if key in row and row[key] is not None and str(row[key]).strip() != "":
            return row[key]
    return None


def _fmt(label: str, value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return f"{label}：{text}"


def _normalize_scalar(value: Any) -> Any:
    """保留数字 id；其余转 strip 后的字符串。"""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    text = str(value).strip()
    # 纯数字且无多余前导零时转为 int（便于 id / *Id 字段）
    if text.isdigit() and (text == "0" or not text.startswith("0")):
        try:
            return int(text)
        except ValueError:
            return text
    return text


def map_row_to_entity(table_name: str, row: dict[str, Any], row_index: int) -> dict[str, Any]:
    """
    将一行映射为实体同步记录。

    返回字段：entity_key, source, entity_type, text, payload
    """
    table = (table_name or "").strip().lower()
    if table == "p_device":
        return _map_device(row, row_index)
    if table == "p_device_variable":
        return _map_variable(row, row_index)
    return _map_generic(table, row, row_index)


def _extract_device_fields(row: dict[str, Any]) -> dict[str, Any]:
    """
    从达梦行提取设备白名单字段。

    明确不写入 password（即使源表有该列），避免凭据进入向量库与 Prompt。
    """
    out: dict[str, Any] = {}
    for key in _DEVICE_PAYLOAD_KEYS:
        aliases = _DEVICE_COLUMN_ALIASES.get(key, (key.lower(),))
        # 同时兼容行内已是 camelCase / 小写 camel 的键
        candidates = (*aliases, key, key.lower())
        raw = _pick(row, *candidates)
        if raw is None:
            continue
        out[key] = _normalize_scalar(raw)
    return out


def _map_device(row: dict[str, Any], row_index: int) -> dict[str, Any]:
    fields = _extract_device_fields(row)
    code = fields.get("deviceCode")
    device_id = fields.get("id")
    entity_key = str(code or device_id or f"row-{row_index}").strip()

    parts = [_fmt(label, fields.get(key)) for key, label in _DEVICE_TEXT_LABELS]
    text = "；".join(p for p in parts if p) or f"设备行 {row_index}"
    source = f"dm:device:{entity_key}"
    return {
        "entity_key": entity_key,
        "source": source,
        "entity_type": "device",
        "text": text,
        "payload": fields,
    }


def _map_variable(row: dict[str, Any], row_index: int) -> dict[str, Any]:
    var_name = _pick(row, "var_name", "varname", "var_code", "varcode", "name")
    show_name = _pick(row, "show_name", "showname", "display_name")
    device_code = _pick(row, "device_code", "devicecode", "dn")
    device_name = _pick(row, "device_name", "devicename")
    device_id = _pick(row, "device_id", "deviceid")
    entity_key = f"{device_code or 'unknown'}:{var_name or row_index}"
    parts = [
        _fmt("变量编码", var_name),
        _fmt("变量名称", show_name),
        _fmt("所属设备编码", device_code),
        _fmt("所属设备名称", device_name),
    ]
    text = "；".join(p for p in parts if p) or f"变量行 {row_index}"
    source = f"dm:variable:{entity_key}"
    return {
        "entity_key": entity_key,
        "source": source,
        "entity_type": "variable",
        "text": text,
        "payload": {
            "table": "p_device_variable",
            "var_name": str(var_name) if var_name is not None else None,
            "show_name": str(show_name) if show_name is not None else None,
            "device_code": str(device_code) if device_code is not None else None,
            "device_name": str(device_name) if device_name is not None else None,
            "device_id": str(device_id) if device_id is not None else None,
        },
    }


def _map_generic(table: str, row: dict[str, Any], row_index: int) -> dict[str, Any]:
    # 优先常见主键列
    pk = _pick(row, "id", "pk_id", "uuid", "code", "name")
    entity_key = str(pk if pk is not None else row_index)
    pairs: list[str] = []
    for key, value in row.items():
        if value is None:
            continue
        text = str(value).strip()
        if not text:
            continue
        # 单字段过长截断，避免 embedding 爆炸
        if len(text) > 200:
            text = text[:200] + "…"
        pairs.append(f"{key}={text}")
        if len(pairs) >= 24:
            break
    body = "；".join(pairs) if pairs else f"空行 {row_index}"
    text = f"表 {table}：{body}"
    source = f"dm:table:{table}:{entity_key}"
    return {
        "entity_key": entity_key,
        "source": source,
        "entity_type": "table_row",
        "text": text,
        "payload": {"table": table},
    }
