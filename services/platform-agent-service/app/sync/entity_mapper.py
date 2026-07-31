"""表行 → 向量化文本 / payload。"""

from __future__ import annotations

from typing import Any


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


def _map_device(row: dict[str, Any], row_index: int) -> dict[str, Any]:
    code = _pick(row, "device_code", "devicecode", "dn", "code")
    name = _pick(row, "device_name", "devicename", "name")
    entity_key = str(code or f"row-{row_index}").strip()
    parts = [
        _fmt("设备编码", code),
        _fmt("设备名称", name),
        _fmt("区域", _pick(row, "area_name", "areaname", "area")),
        _fmt("类型", _pick(row, "device_type_name", "devicetypename", "type_name")),
        _fmt("分组", _pick(row, "device_group_name", "devicegroupname")),
        _fmt("启用状态", _pick(row, "device_status", "devicestatus", "enable_status")),
        _fmt("在线状态", _pick(row, "online_status", "onlinestatus")),
    ]
    text = "；".join(p for p in parts if p) or f"设备行 {row_index}"
    source = f"dm:device:{entity_key}"
    return {
        "entity_key": entity_key,
        "source": source,
        "entity_type": "device",
        "text": text,
        "payload": {
            "table": "p_device",
            "device_code": str(code) if code is not None else None,
            "device_name": str(name) if name is not None else None,
        },
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
