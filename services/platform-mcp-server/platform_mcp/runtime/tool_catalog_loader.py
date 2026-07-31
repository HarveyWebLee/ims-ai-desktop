"""
从 app/tools/catalog.json 加载工具 manifest。

文件职责
--------
把 ``packages/agent-core/tool-catalog.ts`` 经 ``export_catalog.py`` 导出的 JSON
读进 Python，供 preflight、plan_confirm 风险分级、Prompt 表格、HITL 字段推导使用，
避免与 TypeScript 包重复维护两份定义。

在 Agent 流程中的位置
--------------------
契约层读取器（不做 HTTP、不执行工具）：
  tool_preflight / prompt_assembly / HITL 组装
    → get_tool_manifest / get_schema_required / get_preflight_config
    → hitl_fields_for_missing / format_registered_tools_bindings

如何被调用
----------
- ``tool_preflight``：schema 缺参、catalog preflight 声明、platform_api 映射
- ``prompt_assembly.format_registered_tools_bindings``：转调本模块同名实现
- 风险集合：``get_tools_by_risk("high", "medium")``

白话解释
--------
catalog.json 就是「工具说明书合订本」。本模块负责翻书：查某工具必填参数、
风险等级、对应哪个平台 HTTP、缺参时表格字段怎么画。
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from platform_mcp.runtime.paths import mcp_catalog_path

_CATALOG_PATH = mcp_catalog_path()


@lru_cache(maxsize=1)
def load_tool_catalog() -> list[dict[str, Any]]:
    """
    加载全部已启用工具 manifest；文件缺失时返回空列表。

    进程内 lru_cache：只读盘一次。enabled=false 的条目会被过滤掉。
    """
    if not _CATALOG_PATH.exists():
        return []
    data = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [t for t in data if isinstance(t, dict) and t.get("enabled", True)]
    return []


def get_tool_manifest(tool_name: str) -> dict[str, Any] | None:
    """按 snake_case 工具名获取 manifest 条目；未注册返回 None。"""
    name = (tool_name or "").strip()
    for tool in load_tool_catalog():
        if str(tool.get("name") or "") == name:
            return tool
    return None


def parse_platform_api_ref(platform_api: str | None) -> tuple[str, str] | None:
    """
    解析 catalog platform_api 字段为 (path, method)。

    示例: ``POST /api/app/alarm/getAlarmList`` → ``('/alarm/getAlarmList', 'POST')``

    业务规则:
        - 空或「—」表示无平台 API（多为 client 工具）
        - 去掉 /api/app 或 /api 前缀，与 platform_api_index 的 path 对齐
    """
    raw = str(platform_api or "").strip()
    if not raw or raw == "—":
        return None
    parts = raw.split(None, 1)
    if len(parts) != 2:
        return None
    method, full_path = parts[0].upper(), parts[1].strip()
    # 去掉 /api/app 前缀，与 platform_api_index 的 path 对齐
    for prefix in ("/api/app", "/api"):
        if full_path.startswith(prefix):
            full_path = full_path[len(prefix) :] or full_path
            break
    if not full_path.startswith("/"):
        full_path = "/" + full_path
    return full_path, method


def get_tool_platform_api(tool_name: str) -> tuple[str, str] | None:
    """从 manifest 读取平台 API path + method。"""
    manifest = get_tool_manifest(tool_name)
    if not manifest:
        return None
    return parse_platform_api_ref(str(manifest.get("platform_api") or ""))


def get_preflight_config(tool_name: str) -> dict[str, Any] | None:
    """
    读取 catalog preflight 声明。

    常见键: alarm_time / one_of / when_resource —— 由 tool_preflight 解释执行。
    """
    manifest = get_tool_manifest(tool_name)
    if not manifest:
        return None
    cfg = manifest.get("preflight")
    return dict(cfg) if isinstance(cfg, dict) else None


def format_registered_tools_bindings() -> str:
    """
    从 catalog.json 生成「已注册工具 ↔ 平台接口」Markdown 表格。

    替代 prompt_assembly 内硬编码列表；client 侧工具平台接口显示为「—」。
    """
    lines = [
        "## 已注册工具与平台接口",
        "",
        "| 工具 | 平台接口 | 用途 |",
        "|------|----------|------|",
    ]
    for tool in load_tool_catalog():
        name = str(tool.get("name") or "")
        if not name:
            continue
        side = str(tool.get("side") or "server")
        api_ref = str(tool.get("platform_api") or "")
        if side == "client" or not api_ref:
            api_cell = "—"
        else:
            parsed = parse_platform_api_ref(api_ref)
            api_cell = f"{parsed[1]} {parsed[0]}" if parsed else api_ref
        desc = str(tool.get("description") or name).replace("\n", " ")[:36]
        lines.append(f"| `{name}` | {api_cell} | {desc} |")
    lines.append("")
    lines.append(
        "未上表的平台能力（1526+ API）不在 Agent 白名单内；新增能力须先注册到 tool-catalog 再开放。"
    )
    return "\n".join(lines)


def get_schema_required(tool_name: str) -> list[str]:
    """读取 parameters.required（JSON Schema）。"""
    manifest = get_tool_manifest(tool_name)
    if not manifest:
        return []
    params = manifest.get("parameters")
    if not isinstance(params, dict):
        return []
    required = params.get("required")
    if not isinstance(required, list):
        return []
    return [str(r) for r in required if r]


def get_schema_properties(tool_name: str) -> dict[str, Any]:
    """读取 parameters.properties。"""
    manifest = get_tool_manifest(tool_name)
    if not manifest:
        return {}
    params = manifest.get("parameters")
    if not isinstance(params, dict):
        return {}
    props = params.get("properties")
    return dict(props) if isinstance(props, dict) else {}


def get_hitl_fields(tool_name: str) -> list[dict[str, Any]]:
    """读取 catalog 声明的 HITL 表单字段（含 datetime_range 等）。"""
    manifest = get_tool_manifest(tool_name)
    if not manifest:
        return []
    fields = manifest.get("hitl_fields")
    if isinstance(fields, list):
        return [dict(f) for f in fields if isinstance(f, dict) and f.get("name")]
    return []


def get_tools_by_risk(*levels: str) -> frozenset[str]:
    """按 risk_level 筛选工具名集合（如 high → 计划确认门控）。"""
    level_set = {lv.lower() for lv in levels}
    names: set[str] = set()
    for tool in load_tool_catalog():
        risk = str(tool.get("risk_level") or "low").lower()
        if risk in level_set:
            names.add(str(tool["name"]))
    return frozenset(names)


def catalog_property_to_hitl_field(name: str, prop: dict[str, Any]) -> dict[str, Any]:
    """将 catalog JSON Schema 属性转为最简 HITL 字段（string/select）。"""
    field: dict[str, Any] = {
        "name": name,
        "label": str(prop.get("description") or name)[:48],
        "type": "string",
        "required": True,
    }
    enum_vals = prop.get("enum")
    if isinstance(enum_vals, list) and enum_vals:
        field["type"] = "select"
        field["options"] = [{"label": str(v), "value": str(v)} for v in enum_vals]
    desc = prop.get("description")
    if desc:
        field["description"] = str(desc)
    return field


def hitl_fields_for_missing(
    tool_name: str,
    missing: list[str],
    *,
    overrides: dict[str, list[dict[str, Any]]] | None = None,
) -> list[dict[str, Any]]:
    """
    为缺失的 schema 字段生成 HITL 表单定义。

    优先级（业务规则）:
        1. catalog hitl_fields 中与 missing 相交的字段
        2. 若缺 start_time/end_time/time_range → 直接回整套 catalog / override
           （datetime_range 是复合控件，不能拆开只画一半）
        3. overrides（告警类复杂表单兼容回退）
        4. 从 parameters.properties 推导最简 string/select
    """
    catalog_fields = get_hitl_fields(tool_name)
    if catalog_fields:
        missing_set = set(missing)
        filtered = [f for f in catalog_fields if f.get("name") in missing_set]
        if filtered:
            return filtered
        if missing_set & {"start_time", "end_time", "time_range"}:
            return catalog_fields

    if overrides and tool_name in overrides:
        override = overrides[tool_name]
        missing_set = set(missing)
        filtered = [f for f in override if f.get("name") in missing_set]
        if filtered:
            return filtered
        # datetime_range 等复合字段：缺 start_time 时也返回完整 override
        if missing_set & {"start_time", "end_time", "time_range"}:
            return override

    props = get_schema_properties(tool_name)
    fields: list[dict[str, Any]] = []
    for name in missing:
        prop = props.get(name)
        if isinstance(prop, dict):
            fields.append(catalog_property_to_hitl_field(name, prop))
        else:
            fields.append(
                {
                    "name": name,
                    "label": name,
                    "type": "string",
                    "required": True,
                }
            )
    return fields
