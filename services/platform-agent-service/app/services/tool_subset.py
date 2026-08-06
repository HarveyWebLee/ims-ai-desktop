"""
按会话运行模式与意图领域裁剪 create_agent 绑定工具子集。

规则
----
- readonly：仅绑定非写工具
- confirm / autonomous：关键词推断 domains
  - 命中：core ∪ matched（写工具仅在命中领域内出现）
  - 未命中：safe_default = core ∪ 非写工具（**不再**回退全量）
- retrieve_knowledge 与 nav 低风险工具恒保留（core）
- 每 thread 记住上次 chat 的 tool_names（内存 + Postgres），供 resume 复用同一父图
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

from app.infrastructure.persistence.tool_subset_repository import (
    clear_thread_tool_subset,
    configure_tool_subset_persistence,
    get_remembered_thread_tool_subset,
    remember_thread_tool_subset,
)
from contracts.context import normalize_run_mode
from contracts.tool_catalog_loader import (
    get_tools_by_domains,
    is_write_tool,
    load_tool_catalog,
)

logger = logging.getLogger(__name__)

_DOMAIN_KEYWORDS: dict[str, tuple[str, ...]] = {
    "alarm": (
        "告警",
        "报警",
        "确认告警",
        "处理告警",
        "未处理",
        "未确认",
        "alarm",
    ),
    "device": (
        "设备",
        "门禁",
        "开门",
        "关门",
        "播报",
        "变量",
        "下发",
        "指令",
        "实时值",
        "历史曲线",
        "device",
    ),
    "export": ("导出", "下载", "excel", "报表"),
    "duty": ("值班", "岗哨", "交接"),
    "acs": ("出入", "通行记录"),
    "nav": ("跳转", "打开页面", "设施管理", "设备管理", "导航"),
}

# 本地 RAG 工具名（非 catalog）
RETRIEVE_KNOWLEDGE = "retrieve_knowledge"

ToolSubsetStrategy = Literal["domain", "safe_default", "emergency_full"]


@dataclass(frozen=True)
class ToolSubsetResult:
    """单轮工具子集结果。"""

    tool_names: frozenset[str]
    domains: frozenset[str]
    fallback_full: bool
    fingerprint: str
    strategy: ToolSubsetStrategy = "domain"


def tool_subset_fingerprint(tool_names: frozenset[str]) -> str:
    """稳定指纹，用作 create_agent / 父图缓存键。"""
    return ",".join(sorted(tool_names))


def infer_domains_from_text(*texts: str) -> frozenset[str]:
    """轻量关键词领域推断。"""
    blob = "\n".join(t for t in texts if t).lower()
    if not blob.strip():
        return frozenset()
    hit: set[str] = set()
    for domain, keywords in _DOMAIN_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in blob:
                hit.add(domain)
                break
    return frozenset(hit)


def _catalog_tool_names() -> frozenset[str]:
    return frozenset(
        str(t["name"]) for t in load_tool_catalog() if str(t.get("name") or "").strip()
    )


def _nav_core_tools() -> frozenset[str]:
    """nav 领域低风险工具（恒保留）。"""
    names: set[str] = set()
    for name in get_tools_by_domains("nav"):
        if not is_write_tool(name):
            names.add(name)
    return frozenset(names)


def _filter_by_run_mode(names: frozenset[str], run_mode: str) -> frozenset[str]:
    mode = normalize_run_mode(run_mode)
    if mode != "readonly":
        return names
    return frozenset(n for n in names if n == RETRIEVE_KNOWLEDGE or not is_write_tool(n))


def _safe_default_subset(allowed: frozenset[str], core: frozenset[str]) -> frozenset[str]:
    """
    无领域命中时的默认子集：core ∪ 非写工具。

    写工具必须等 domains 命中后再进入绑定集，避免闲聊/泛化意图绑定全量写能力。
    """
    reads = frozenset(n for n in allowed if n == RETRIEVE_KNOWLEDGE or not is_write_tool(n))
    return (core | reads) & allowed


def select_tool_subset(
    *,
    run_mode: str,
    message: str,
    recent_user_messages: list[str] | None = None,
    available_names: frozenset[str] | None = None,
) -> ToolSubsetResult:
    """
    计算本轮应绑定的工具名集合。

    available_names：底层已加载的 MCP+本地工具名；None 时仅用 catalog + retrieve_knowledge。
    """
    mode = normalize_run_mode(run_mode)
    catalog_names = _catalog_tool_names()
    base = frozenset(available_names) if available_names is not None else catalog_names
    # 始终允许本地 RAG
    universe = frozenset(base | {RETRIEVE_KNOWLEDGE})
    allowed = _filter_by_run_mode(universe, mode)

    recent = list(recent_user_messages or [])
    domains = infer_domains_from_text(message, *recent[-4:])
    core = frozenset({RETRIEVE_KNOWLEDGE}) | (_nav_core_tools() & allowed)

    strategy: ToolSubsetStrategy
    fallback_full = False
    if domains:
        matched = get_tools_by_domains(*domains) & allowed
        if matched:
            selected = (core | matched) & allowed
            strategy = "domain"
        else:
            # 关键词命中但 catalog 无对应工具：仍不回退全量
            selected = _safe_default_subset(allowed, core)
            strategy = "safe_default"
    else:
        selected = _safe_default_subset(allowed, core)
        strategy = "safe_default"

    # 防御：空集时回退允许集（仅此路径标记 fallback_full）
    if not selected:
        fallback_full = True
        strategy = "emergency_full"
        selected = allowed if allowed else frozenset({RETRIEVE_KNOWLEDGE})

    fp = tool_subset_fingerprint(selected)
    logger.info(
        "tool_subset: mode=%s domains=%s strategy=%s fallback=%s tools=%s",
        mode,
        sorted(domains),
        strategy,
        fallback_full,
        sorted(selected),
    )
    return ToolSubsetResult(
        tool_names=selected,
        domains=domains,
        fallback_full=fallback_full,
        fingerprint=fp,
        strategy=strategy,
    )


def deny_readonly_write_summary(tool_name: str) -> str:
    """只读模式下写工具拒绝摘要。"""
    return (
        f"当前为只读模式，无法执行写操作工具「{tool_name}」。"
        "请将运行模式切换为「确认执行」或「自主」后再试。"
    )


__all__ = [
    "RETRIEVE_KNOWLEDGE",
    "ToolSubsetResult",
    "ToolSubsetStrategy",
    "clear_thread_tool_subset",
    "configure_tool_subset_persistence",
    "deny_readonly_write_summary",
    "get_remembered_thread_tool_subset",
    "infer_domains_from_text",
    "remember_thread_tool_subset",
    "select_tool_subset",
    "tool_subset_fingerprint",
]
