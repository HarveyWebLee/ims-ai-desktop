"""
平台 OpenAPI 索引读取与检索服务。

文件职责
--------
提供「平台 HTTP API 元数据」的只读查询能力：按 path/method 查单条、
按 tag 列表、关键词搜索、格式化为 Prompt 摘要、浅层必填校验。

Agent 不能直接翻 14 万行 swaggerApi.json；本模块只读预导出的轻量 JSON。

在 Agent 流程中的位置
--------------------
偏「研发与 Prompt / preflight 支撑层」，不直接对前端暴露 HTTP：
  tools / preflight / prompt_assembly
    → get_api / validate_request_fields / format_*_for_prompt
    → 对照索引补全参数说明或拦截缺参

如何被调用
----------
- `tool_preflight._preflight_platform_api_payload` → `validate_request_fields`
- `prompt_assembly.format_alarm_api_compact` → `get_api` / `list_apis_by_tag`
- 研发调试时可直接 `search_apis("告警")`

白话解释
--------
把平台接口说明书裁成一本「目录册」：工具开发时查 path，
给模型的 system prompt 塞几行摘要，invoke 前对照「必填字段」做一次浅检查。

数据源
------
- ``app/data/platform_api_index.json``（scripts/export_api_index.py 从 swagger 导出）
- ``app/data/platform_api_tags.json``（各 tag 的 API 数量摘要）
"""

from __future__ import annotations

# ── 标准库 ──
import json
import re
from functools import lru_cache  # 装饰器：缓存函数返回值，避免重复读文件
from pathlib import Path
from typing import Any

# 数据目录：app/data/
from platform_mcp.runtime.settings import settings

_DATA_DIR = Path(settings.agent_data_dir)
_INDEX_PATH = _DATA_DIR / "platform_api_index.json"
_TAG_SUMMARY_PATH = _DATA_DIR / "platform_api_tags.json"


@lru_cache(maxsize=1)
def _load_index() -> dict[str, Any]:
    """
    加载 platform_api_index.json（进程内只读一次，结果缓存）。

    返回:
        索引 dict，含 apis、byTag、pathCount 等键；文件不存在时返回空结构
        （空结构表示「没有目录册」，调用方应降级为不校验 / 无摘要）。
    """
    if not _INDEX_PATH.exists():
        return {"apis": [], "byTag": {}, "pathCount": 0}
    return json.loads(_INDEX_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _load_tag_summary() -> list[dict[str, Any]]:
    """
    加载 tag 摘要 JSON（进程内缓存）。

    返回:
        tag 列表，每项含 tag 名、API 数量等
    """
    if not _TAG_SUMMARY_PATH.exists():
        return []
    return json.loads(_TAG_SUMMARY_PATH.read_text(encoding="utf-8"))


def get_api(path: str, method: str = "POST") -> dict[str, Any] | None:
    """
    按 path + HTTP method 获取单条 API 元数据。

    参数:
        path: 接口路径，如 "/alarm/getAlarmList"
        method: HTTP 方法，默认 POST（内部统一 upper）

    返回:
        API 元数据 dict（含 requestProperties、required、summary 等），未找到返回 None
    """
    method = method.upper()
    for api in _load_index().get("apis") or []:
        if api.get("path") == path and api.get("method") == method:
            return api
    return None


def list_apis_by_tag(tag: str) -> list[dict[str, Any]]:
    """
    列出某 OpenAPI tag 下的全部 API。

    参数:
        tag: 如 "alarmManagementApi"

    返回:
        该 tag 下所有 API 元数据列表
    """
    paths = (_load_index().get("byTag") or {}).get(tag) or []
    path_set = set(paths)  # set 用于 O(1) 成员判断
    return [api for api in _load_index().get("apis") or [] if api.get("path") in path_set]


def search_apis(
    query: str,
    *,
    tag: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """
    关键词搜索 path / summary / operationId。

    供研发调试或后续 Agent「API 发现」工具使用。

    参数:
        query: 搜索关键词（空则直接返回 []）
        tag: 可选，限定在某个 tag 内搜索
        limit: 最多返回条数

    返回:
        匹配的 API 元数据列表
    """
    q = query.strip().lower()
    if not q:
        return []

    results: list[dict[str, Any]] = []
    for api in _load_index().get("apis") or []:
        if tag and tag not in (api.get("tags") or []):
            continue
        # filter(None, [...]) 去掉 None/空串，再 join 成搜索 haystack
        haystack = " ".join(
            filter(
                None,
                [
                    api.get("path"),
                    api.get("summary"),
                    api.get("operationId"),
                    " ".join(api.get("tags") or []),
                ],
            )
        ).lower()
        # 子串匹配，或 query 每个词都在 haystack 中
        if q in haystack or all(part in haystack for part in re.split(r"\s+", q)):
            results.append(api)
        if len(results) >= limit:
            break
    return results


def format_api_for_prompt(api: dict[str, Any]) -> str:
    """
    将单条 API 格式化为 Prompt 友好的一行 Markdown。

    参数:
        api: get_api 返回的元数据 dict

    返回:
        如 "- `POST /alarm/getAlarmList` — 获取告警列表（参数: startTime*, ...）"
        （带 * 的为索引声明的必填字段）
    """
    props = api.get("requestProperties") or {}
    required = set(api.get("required") or [])
    param_bits: list[str] = []
    for name in props:
        if name in required:
            param_bits.append(f"{name}*")  # * 表示必填
        elif len(param_bits) < 6:
            param_bits.append(name)
    param_str = ", ".join(param_bits[:8])
    if len(props) > 8:
        param_str += ", ..."
    return f"- `{api.get('method')} {api.get('path')}` — {api.get('summary') or '（无摘要）'}" + (
        f"（参数: {param_str}）" if param_str else ""
    )


def format_tag_summary_for_prompt(tag: str, *, max_apis: int = 12) -> str:
    """
    为指定 tag 生成 API 摘要块，可注入 system prompt。

    参数:
        tag: OpenAPI tag 名
        max_apis: 最多包含几条 API

    返回:
        Markdown 块；无 API 时返回空字符串
    """
    apis = list_apis_by_tag(tag)[:max_apis]
    if not apis:
        return ""
    lines = [f"### 平台 API 参考（{tag}）", ""]
    lines.extend(format_api_for_prompt(a) for a in apis)
    return "\n".join(lines)


def get_tag_overview() -> list[dict[str, Any]]:
    """
    返回各 tag 的 API 数量与示例摘要。

    返回:
        tag 摘要列表（来自 platform_api_tags.json）
    """
    return _load_tag_summary()


def validate_request_fields(path: str, payload: dict[str, Any], method: str = "POST") -> list[str]:
    """
    对照 swagger 导出索引做浅层 preflight：检查必填项是否齐全。

    业务规则:
        - 索引里找不到该 API → 返回空列表（不阻断调用，避免误杀）
        - 字段为 None 或纯空白字符串 → 视为缺失

    参数:
        path: API 路径
        payload: 待发送的请求体 dict
        method: HTTP 方法

    返回:
        缺失的必填字段名列表
    """
    api = get_api(path, method)
    if not api:
        return []
    missing: list[str] = []
    for field in api.get("required") or []:
        val = payload.get(field)
        # None 或空字符串视为缺失
        if val is None or (isinstance(val, str) and not val.strip()):
            missing.append(field)
    return missing
