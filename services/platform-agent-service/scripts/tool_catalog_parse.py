"""
从 packages/agent-core/tool-catalog.ts 解析完整工具 manifest（供 export_catalog.py 使用）。

文件职责
--------
把 TypeScript 里的「工具目录」读成 Python 可用的 list[dict]。
不用 Node/TypeScript 编译器，而是用「括号配对 + 正则」从 .ts 文本抠字段，
再交给 export_catalog.py 写成 app/tools/catalog.json。

白话概念
--------
tool-catalog.ts 是前后端共享的「工具说明书」唯一数据源（工具名、参数、风险级等）。
Python Agent 读不懂 .ts，所以导出成 JSON；本模块负责「读懂 TS 文本」这一步。

如何被调用
----------
  一般由 scripts/export_catalog.py 间接调用；也可单独：
  uv run python -c "from scripts.tool_catalog_parse import parse_tool_catalog; ..."

实现策略
--------
采用大括号匹配 + 正则提取，避免引入 Node 依赖；覆盖当前 catalog 结构即可扩展。
"""

from __future__ import annotations

import json
import re
from typing import Any


def _extract_braced(text: str, open_index: int) -> str:
    """从 open_index 处的 `{` 提取到匹配的 `}`（含引号内括号）。"""
    if open_index >= len(text) or text[open_index] != "{":
        raise ValueError("expected '{' at open_index")
    depth = 0
    in_string: str | None = None
    escape = False
    for i in range(open_index, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if in_string:
            if ch == in_string:
                in_string = None
            continue
        if ch in ("'", '"'):
            in_string = ch
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[open_index : i + 1]
    raise ValueError("unbalanced braces")


def _extract_bracketed(text: str, open_index: int) -> str:
    """从 open_index 处的 `[` 提取到匹配的 `]`（含引号内括号）。"""
    if open_index >= len(text) or text[open_index] != "[":
        raise ValueError("expected '[' at open_index")
    depth = 0
    in_string: str | None = None
    escape = False
    for i in range(open_index, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if in_string:
            if ch == in_string:
                in_string = None
            continue
        if ch in ("'", '"'):
            in_string = ch
            continue
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return text[open_index : i + 1]
    raise ValueError("unbalanced brackets")


def _split_catalog_objects(array_body: str) -> list[str]:
    """将 PLATFORM_TOOL_CATALOG 数组体切分为各工具对象字符串。"""
    objects: list[str] = []
    i = 0
    length = len(array_body)
    while i < length:
        start = array_body.find("{", i)
        if start < 0:
            break
        block = _extract_braced(array_body, start)
        objects.append(block)
        i = start + len(block)
    return objects


def _parse_concatenated_description(block: str) -> str:
    """
    解析 TS 中 description 字段（支持多段 '...' + '...' 拼接）。
    """
    m = re.search(r"description:\s*", block)
    if not m:
        return ""
    rest = block[m.end() :]
    stop = re.search(
        r"\n\s*(parameters|side|risk_level|enabled|platform_api|client_action|required_permissions)\s*:",
        rest,
    )
    if stop:
        rest = rest[: stop.start()]
    matches = re.findall(
        r"'((?:[^'\\]|\\.)*)'|\"((?:[^\"\\]|\\.)*)\"",
        rest,
        re.DOTALL,
    )
    parts = [single or double for single, double in matches]
    if not parts:
        single = _parse_string_field(block, "description")
        return single or ""
    return "".join(part.replace("\\'", "'").replace('\\"', '"') for part in parts)


def _parse_string_field(block: str, field: str) -> str | None:
    m = re.search(rf"{field}:\s*['\"]([^'\"]*)['\"]", block)
    return m.group(1) if m else None


def _parse_bool_field(block: str, field: str, default: bool = True) -> bool:
    m = re.search(rf"{field}:\s*(true|false)", block)
    if not m:
        return default
    return m.group(1) == "true"


def _parse_string_list_field(block: str, field: str) -> list[str]:
    m = re.search(rf"{field}:\s*\[(.*?)\]", block, re.DOTALL)
    if not m:
        return []
    return re.findall(r"['\"]([^'\"]+)['\"]", m.group(1))


def _collapse_ts_string_concat(text: str) -> str:
    """合并 TS 对象内单双引号字符串拼接，便于 json.loads。"""
    patterns = (
        (re.compile(r"'((?:[^'\\]|\\.)*)'\s*\+\s*'((?:[^'\\]|\\.)*)'"), "'"),
        (re.compile(r'"((?:[^"\\]|\\.)*)"\s*\+\s*"((?:[^"\\]|\\.)*)"'), '"'),
    )
    prev: str | None = None
    while prev != text:
        prev = text
        for pattern, quote in patterns:
            text = pattern.sub(
                lambda match, delimiter=quote: (
                    delimiter + match.group(1) + match.group(2) + delimiter
                ),
                text,
            )
    return text


def _js_object_to_json_dict(raw: str) -> dict[str, Any]:
    """
    将 TS/JS 对象字面量转为 dict（仅支持 catalog 用到的子集）。

    策略：补引号 → json.loads；失败时返回空 dict。
    """
    text = raw.strip()
    # 去掉 // 行注释
    text = re.sub(r"//[^\n]*", "", text)
    # 合并 TS 多段字符串拼接
    text = _collapse_ts_string_concat(text)
    # 未加引号的 key → 加引号
    text = re.sub(r"(\s|^)([a-zA-Z_][\w]*)\s*:", r'\1"\2":', text)
    # 单引号字符串 → 双引号（description 内无嵌套单引号）
    text = re.sub(r"'([^'\\]*)'", r'"\1"', text)
    # 尾随逗号
    text = re.sub(r",\s*}", "}", text)
    text = re.sub(r",\s*]", "]", text)
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def _parse_parameters(block: str) -> dict[str, Any]:
    m = re.search(r"parameters:\s*(\{)", block)
    if not m:
        return {"type": "object", "properties": {}, "required": []}
    raw = _extract_braced(block, m.start(1))
    parsed = _js_object_to_json_dict(raw)
    if not parsed:
        return {"type": "object", "properties": {}, "required": []}
    parsed.setdefault("type", "object")
    parsed.setdefault("properties", {})
    parsed.setdefault("required", [])
    return parsed


def _parse_hitl_field_array(raw: str) -> list[dict[str, Any]]:
    """解析 HITL 字段对象数组。"""
    fields: list[dict[str, Any]] = []
    for block in _split_catalog_objects(raw[1:-1]):
        parsed = _js_object_to_json_dict(block)
        if parsed.get("name"):
            fields.append(parsed)
    return fields


def _parse_hitl_field_constants(content: str) -> dict[str, list[dict[str, Any]]]:
    """解析全部导出的 `*_HITL_FIELDS` 常量，避免新增设备字段时修改脚本。"""
    constants: dict[str, list[dict[str, Any]]] = {}
    pattern = re.compile(r"export const ([A-Z_][\w]*_HITL_FIELDS)[^=]*=\s*\[")
    for match in pattern.finditer(content):
        raw = _extract_bracketed(content, match.end() - 1)
        fields = _parse_hitl_field_array(raw)
        if fields:
            constants[match.group(1)] = fields
    return constants


def _parse_hitl_fields(
    block: str, *, constants: dict[str, list[dict[str, Any]]]
) -> list[dict[str, Any]] | None:
    """解析 hitl_fields 的常量引用或内联对象数组。"""
    ref = re.search(r"hitl_fields:\s*([A-Z_][\w]*)", block)
    if ref:
        fields = constants.get(ref.group(1), [])
        return list(fields) if fields else None
    inline = re.search(r"hitl_fields:\s*\[", block)
    if inline:
        fields = _parse_hitl_field_array(_extract_bracketed(block, inline.end() - 1))
        return fields or None
    return None


def _parse_preflight(block: str) -> dict[str, Any] | None:
    """解析 preflight: { alarm_time, when_resource, one_of }。"""
    match = re.search(r"preflight:\s*(\{)", block)
    if not match:
        return None
    raw = _extract_braced(block, match.start(1))
    result: dict[str, Any] = {}
    if re.search(r"alarm_time:\s*true", raw):
        result["alarm_time"] = True
    # when_resource 支持字符串或字符串数组
    when_list = _parse_string_list_field(raw, "when_resource")
    if when_list:
        result["when_resource"] = when_list if len(when_list) > 1 else when_list[0]
    else:
        when = _parse_string_field(raw, "when_resource")
        if when:
            result["when_resource"] = when
    # one_of: [['alarm_ids'], ['start_time', 'end_time']]
    one_match = re.search(r"one_of:\s*\[", raw)
    if one_match:
        depth = 0
        start = one_match.start()
        for i in range(start, len(raw)):
            if raw[i] == "[":
                depth += 1
            elif raw[i] == "]":
                depth -= 1
                if depth == 0:
                    one_raw = raw[start : i + 1]
                    groups = re.findall(r"\[([^\]]*)\]", one_raw)
                    parsed_groups: list[list[str]] = []
                    for g in groups:
                        fields = re.findall(r"['\"]([^'\"]+)['\"]", g)
                        if fields:
                            parsed_groups.append(fields)
                    if parsed_groups:
                        result["one_of"] = parsed_groups
                    break
    return result or None


def parse_tool_object(
    block: str, *, hitl_constants: dict[str, list[dict[str, Any]]] | None = None
) -> dict[str, Any] | None:
    """解析单个工具对象块为 manifest dict。"""
    name = _parse_string_field(block, "name")
    if not name:
        return None
    item: dict[str, Any] = {
        "name": name,
        "description": _parse_concatenated_description(block),
        "parameters": _parse_parameters(block),
        "side": _parse_string_field(block, "side") or "server",
        "risk_level": _parse_string_field(block, "risk_level") or "low",
        "enabled": _parse_bool_field(block, "enabled", True),
    }
    platform_api = _parse_string_field(block, "platform_api")
    if platform_api:
        item["platform_api"] = platform_api
    client_action = _parse_string_field(block, "client_action")
    if client_action:
        item["client_action"] = client_action
    perms = _parse_string_list_field(block, "required_permissions")
    if perms:
        item["required_permissions"] = perms
    domains = _parse_string_list_field(block, "domains")
    if domains:
        item["domains"] = domains
    constants = hitl_constants or {}
    hitl = _parse_hitl_fields(block, constants=constants)
    if hitl:
        item["hitl_fields"] = hitl
    preflight = _parse_preflight(block)
    if preflight:
        item["preflight"] = preflight
    return item


def parse_ts_tool_catalog(content: str) -> list[dict[str, Any]]:
    """从 tool-catalog.ts 全文解析 PLATFORM_TOOL_CATALOG。"""
    hitl_constants = _parse_hitl_field_constants(content)
    match = re.search(
        r"export const PLATFORM_TOOL_CATALOG.*?=\s*\[(.*)\];",
        content,
        re.DOTALL,
    )
    if not match:
        raise ValueError("未找到 PLATFORM_TOOL_CATALOG")

    objects = _split_catalog_objects(match.group(1))
    items: list[dict[str, Any]] = []
    for block in objects:
        parsed = parse_tool_object(block, hitl_constants=hitl_constants)
        if parsed:
            items.append(parsed)
    return items
