"""
从 Swagger 文档导出「轻量级 API 索引」。

【这个脚本是干什么的？】
平台后端有一份完整的 OpenAPI/Swagger 文档（swaggerApi.json），体积很大。
Agent 在写工具、拼 Prompt、校验参数时，不需要整份文档，只需要：
  - 每个接口的路径、HTTP 方法
  - 请求体有哪些字段、是否必填
  - 按 tag 分组的大致摘要

约定：swaggerApi.json = 构建源；本脚本输出 = 运行时资产（勿与 prj-docs RAG 混放）。

本脚本读取 swaggerApi.json，生成两个较小的 JSON 文件：
  - app/data/platform_api_index.json   — 全量 API 索引（运行时）
  - app/data/platform_api_tags.json    — 按 tag 聚合的摘要（运行时）

【如何运行？】
  cd platform-agent-service
  uv run python scripts/export_api_index.py

【Python 小白提示】
  - `from __future__ import annotations`：让类型注解更灵活（Python 3.7+ 常用写法）
  - `Path`： pathlib 模块，用面向对象的方式表示文件路径，比字符串拼接更安全
  - `if __name__ == "__main__"`：只有「直接运行本文件」时才执行下面的代码；
    若被其他文件 import，则不会自动执行 main()
"""

# 启用「延迟注解」：函数签名里可以写还没定义的类型名
from __future__ import annotations

import json  # 读写 JSON 文件
import sys  # 系统相关，这里用来向 stderr 打印警告、返回退出码
from pathlib import Path  # 跨平台路径对象
from typing import Any  # Any 表示「任意类型」，常用于 JSON 解析后的 dict

# ---------------------------------------------------------------------------
# 路径常量：用 Path 拼接，避免 Windows/Linux 斜杠不一致
# ---------------------------------------------------------------------------

# __file__ 是当前 .py 文件的路径；.resolve() 转成绝对路径；.parent 是上一级目录
# scripts/export_api_index.py → parent 是 scripts → parent.parent 是 platform-agent-service
SERVICE_ROOT = Path(__file__).resolve().parent.parent

# 输入：Swagger 原始文件
SWAGGER_PATH = SERVICE_ROOT / "app/data/swaggerApi.json"

# 输出：API 索引与 tag 摘要
OUT_INDEX_JSON = SERVICE_ROOT / "app/data/platform_api_index.json"
OUT_TAG_SUMMARY_JSON = SERVICE_ROOT / "app/data/platform_api_tags.json"

# 与 packages/agent-core/tool-catalog.ts 里 platform_api 字段对齐
# dict[str, str] = 「键和值都是字符串的字典」
# 用于导出后校验：手写工具引用的 path 是否在 swagger 里存在
KNOWN_TOOL_APIS: dict[str, str] = {
    "query_alarms": "/alarm/getAlarmList",
    "get_alarm_detail": "/alarm/getAlarmList",
    "download_file": "/alarm/exportAlarm",
    "batch_confirm_alarms": "/alarm/confirmAlarm",
    "batch_process_alarms": "/alarm/processAlarm",
    "query_devices": "/device/getDeviceList",
    "get_device_detail": "/device/getDeviceByCode/{deviceCode}",
    "query_device_variables": "/device/getVarListByCode",
    "send_device_cmd": "/device/sendCmd",
}


def _resolve_ref(spec: dict[str, Any], ref: str, depth: int = 0) -> dict[str, Any]:
    """
    解析 Swagger 里的 $ref 引用（例如 #/components/schemas/AlarmQueryDTO）。

    Swagger 里经常不写完整 schema，只写 "$ref": "#/components/schemas/XXX"，
    需要按路径在 spec 树里一层层找下去。

    参数:
        spec: 整个 swagger 解析后的 dict（根对象）
        ref:  引用字符串，通常以 "#/ 开头"
        depth: 当前递归深度，防止循环引用导致无限递归（最多 2 层）

    返回:
        解析后的 schema 字典；找不到或类型不对则返回空 dict {}
    """
    # 只处理以 #/ 开头的内部引用
    if not ref.startswith("#/"):
        return {}

    # "#/components/schemas/Foo" → ["components", "schemas", "Foo"]
    parts = ref.lstrip("#/").split("/")

    # 从 spec 根节点开始，按 parts 逐级 .get(key) 往下走
    node: Any = spec
    for part in parts:
        if not isinstance(node, dict):
            return {}
        node = node.get(part, {})

    # 递归太深或 node 不是 dict，直接返回（或空 dict）
    if depth >= 2 or not isinstance(node, dict):
        return node if isinstance(node, dict) else {}

    # OpenAPI 里常用 allOf 合并多个 schema，这里手动合并 properties 和 required
    if "allOf" in node:
        merged: dict[str, Any] = {"type": "object", "properties": {}, "required": []}
        for item in node["allOf"]:
            if isinstance(item, dict) and "$ref" in item:
                # 子项又是引用，递归解析
                sub = _resolve_ref(spec, item["$ref"], depth + 1)
                merged["properties"].update(sub.get("properties") or {})
                # set(...) 去重后再转回 list
                merged["required"] = list(
                    set(merged.get("required") or []) | set(sub.get("required") or [])
                )
            elif isinstance(item, dict):
                merged["properties"].update(item.get("properties") or {})
                merged["required"] = list(
                    set(merged.get("required") or []) | set(item.get("required") or [])
                )
        return merged

    return node


def _flatten_property(prop: dict[str, Any], spec: dict[str, Any], depth: int = 0) -> dict[str, Any]:
    """
    把 Swagger 里单个字段的定义「压扁」成 Agent 易读的简短 dict。

    只保留 type、description、enum、数组 items 等关键信息，去掉冗余嵌套。

    参数:
        prop:  某个 property 的原始 schema 片段
        spec:  完整 swagger spec（用于解析 $ref）
        depth: 递归深度（传给 _resolve_ref）

    返回:
        例如 {"type": "string", "description": "告警级别", "enum": ["1","2"]}
    """
    if "$ref" in prop:
        prop = _resolve_ref(spec, prop["$ref"], depth)

    out: dict[str, Any] = {}
    if "type" in prop:
        out["type"] = prop["type"]
    if prop.get("description"):
        out["description"] = prop["description"].strip()
    if "enum" in prop:
        out["enum"] = prop["enum"]
    # 数组类型：再解析 items 里元素的类型
    if prop.get("type") == "array" and "items" in prop:
        items = prop["items"]
        if isinstance(items, dict) and "$ref" in items:
            items = _resolve_ref(spec, items["$ref"], depth + 1)
        if isinstance(items, dict):
            out["items"] = {"type": items.get("type", "object")}
    return out


def _extract_request_schema(
    spec: dict[str, Any], operation: dict[str, Any]
) -> tuple[str | None, dict[str, Any], list[str]]:
    """
    从单个 operation（如 post /alarm/getAlarmList）提取请求体 schema。

    返回三元组 (tuple):
        schema_name:  schema 名称（来自 $ref 最后一段），没有则为 None
        properties:   字段名 → 扁平化后的字段描述
        required:     必填字段名列表
    """
    body = operation.get("requestBody") or {}
    content = body.get("content") or {}
    json_body = content.get("application/json") or {}
    schema = json_body.get("schema") or {}

    schema_name: str | None = None
    if "$ref" in schema:
        # "#/components/schemas/Foo" → "Foo"
        schema_name = schema["$ref"].split("/")[-1]
        schema = _resolve_ref(spec, schema["$ref"])

    properties: dict[str, Any] = {}
    # .items() 遍历 dict 的键值对；name 是字段名，prop 是字段 schema
    for name, prop in (schema.get("properties") or {}).items():
        if isinstance(prop, dict):
            flat = _flatten_property(prop, spec)
            if flat:
                properties[name] = flat

    required = list(schema.get("required") or [])
    return schema_name, properties, required


def build_api_index(spec: dict[str, Any]) -> dict[str, Any]:
    """
    遍历 swagger paths，构建完整 API 索引结构。

    参数:
        spec: json.loads 后的 swagger 根对象

    返回:
        包含 apis 列表、byTag 分组、统计信息等的 dict
    """
    paths = spec.get("paths") or {}
    apis: list[dict[str, Any]] = []
    by_tag: dict[str, list[str]] = {}

    # paths 结构: { "/alarm/getAlarmList": { "post": { ...operation... } } }
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            # path_item 里可能还有 parameters、summary 等非 HTTP 方法的键，要过滤
            if method not in ("get", "post", "put", "delete", "patch"):
                continue
            if not isinstance(operation, dict):
                continue

            tags = operation.get("tags") or ["untagged"]
            schema_name, properties, required = _extract_request_schema(spec, operation)

            entry = {
                "path": path,
                "method": method.upper(),  # "post" → "POST"
                "tags": tags,
                "summary": (operation.get("summary") or "").strip(),
                "operationId": operation.get("operationId"),
                "requestSchema": schema_name,
                "requestProperties": properties,
                "required": required,
            }
            apis.append(entry)

            # 同一 path 可能属于多个 tag，分别记入 by_tag
            for tag in tags:
                # setdefault: 若 key 不存在则先设为 []，再 append
                by_tag.setdefault(tag, []).append(path)

    # sort + lambda: 按 path 再按 method 排序
    apis.sort(key=lambda x: (x["path"], x["method"]))

    return {
        "source": "swaggerApi.json",
        "openapi": spec.get("openapi"),
        "info": spec.get("info"),
        "pathCount": len(apis),
        "tagCount": len(by_tag),
        "apis": apis,
        # 每个 tag 下的 path 去重并排序
        "byTag": {k: sorted(set(v)) for k, v in sorted(by_tag.items())},
    }


def build_tag_summary(index: dict[str, Any]) -> list[dict[str, Any]]:
    """
    按 tag 聚合摘要，便于塞进 Prompt 或给研发浏览。

    每个 tag 一行统计 + 最多 8 条「METHOD path — summary」示例。
    """
    tag_map: dict[str, dict[str, Any]] = {}
    for api in index["apis"]:
        for tag in api["tags"]:
            bucket = tag_map.setdefault(
                tag,
                {"tag": tag, "count": 0, "summaries": []},
            )
            bucket["count"] += 1
            if api["summary"]:
                bucket["summaries"].append(f"{api['method']} {api['path']} — {api['summary']}")

    # 按 count 降序排列（接口多的 tag 排前面）
    rows = sorted(tag_map.values(), key=lambda x: -x["count"])
    for row in rows:
        row["summaries"] = row["summaries"][:8]
    return rows


def validate_known_tools(index: dict[str, Any]) -> list[str]:
    """
    校验 KNOWN_TOOL_APIS 里手写工具引用的 path 是否在 swagger 索引中存在。

    返回:
        警告信息字符串列表；无问题则为空列表
    """
    # 集合推导式 {a["path"] for a in ...}：所有 API 的 path 组成 set，查找 O(1)
    known_paths = {a["path"] for a in index["apis"]}
    warnings: list[str] = []
    for tool, path in KNOWN_TOOL_APIS.items():
        if path not in known_paths:
            warnings.append(f"工具 {tool} 引用的 {path} 未在 swagger 中找到")
    return warnings


def main() -> int:
    """
    脚本主入口。

    返回:
        0 表示成功；1 表示失败（例如找不到 swagger 文件）
        在命令行里会通过 SystemExit 把这个数字传给操作系统
    """
    if not SWAGGER_PATH.exists():
        # file=sys.stderr：错误信息打到标准错误流，而不是普通 stdout
        print(f"未找到 swagger 文件：{SWAGGER_PATH}", file=sys.stderr)
        return 1

    print(f"Loading {SWAGGER_PATH} ...")
    # read_text(encoding="utf-8") 读文本；json.loads 把 JSON 字符串转成 Python dict/list
    spec = json.loads(SWAGGER_PATH.read_text(encoding="utf-8"))

    index = build_api_index(spec)
    tag_summary = build_tag_summary(index)

    # parents=True：中间目录不存在则创建；exist_ok=True：已存在不报错
    OUT_INDEX_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_INDEX_JSON.write_text(
        json.dumps(index, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    OUT_TAG_SUMMARY_JSON.write_text(
        json.dumps(tag_summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Exported {index['pathCount']} APIs → {OUT_INDEX_JSON}")
    print(f"Exported {len(tag_summary)} tags → {OUT_TAG_SUMMARY_JSON}")

    warnings = validate_known_tools(index)
    for w in warnings:
        print(f"WARN: {w}", file=sys.stderr)

    return 0


# 仅当「python scripts/export_api_index.py」直接运行时执行
if __name__ == "__main__":
    # raise SystemExit(code) 等价于 sys.exit(code)，结束进程并带上退出码
    raise SystemExit(main())
