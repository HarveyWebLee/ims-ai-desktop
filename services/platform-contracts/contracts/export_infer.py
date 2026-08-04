"""导出 resource 推断与 preflight 共用常量（无平台 HTTP 副作用）。

会话上下文（本轮话 + 近期用户句）由 Agent/MCP 通过 ContextVar 透传，
本模块只做纯函数裁决；其他易漂移工具可复用同一套会话上下文，不限于导出。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# 与告警查询页 TransferModal 一致：平台 exportAlarm 单次 size 上限
EXPORT_ALARM_BATCH_MAX = 30000

# 仅时间范围筛选的非告警导出（preflight 共用时间 HITL）
TIME_ONLY_EXPORT_RESOURCES = frozenset(
    {"sentry_handover", "duty_info", "duty_manage", "acs_record"}
)

SUPPORTED_EXPORT_RESOURCES: tuple[str, ...] = (
    "alarm_report",
    "sentry_handover",
    "duty_info",
    "duty_manage",
    "acs_record",
)

EXPORT_RESOURCE_LABELS: dict[str, str] = {
    "alarm_report": "告警报表",
    "sentry_handover": "岗哨交接",
    "duty_info": "值班信息",
    "duty_manage": "值班管理",
    "acs_record": "出入信息",
}

# HITL / 工具结果里标记：resource 已由用户选定，勿再按歧义清空
EXPORT_RESOURCE_CONFIRMED_KEY = "_export_resource_confirmed"

# 从用户原话推断 download_file.resource（专名优先）
_SENTRY_HANDOVER_RE = re.compile(r"岗哨交接|哨位交接|岗哨.{0,8}交接|交接.{0,8}岗哨")
_DUTY_INFO_RE = re.compile(r"值班信息")
_DUTY_MANAGE_RE = re.compile(r"值班管理")
_ACS_RECORD_RE = re.compile(r"出入信息|出入记录|门禁.{0,6}记录|通行记录")
_ALARM_EXPORT_RE = re.compile(r"告警|报警")

# 会话上下文软信号（无「导出专名」时，用于唯一业务域推断）
_CONTEXT_DOMAIN_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("alarm_report", re.compile(r"告警|报警")),
    ("sentry_handover", re.compile(r"岗哨交接|哨位交接|岗哨")),
    ("duty_info", re.compile(r"值班信息")),
    ("duty_manage", re.compile(r"值班管理")),
    ("acs_record", re.compile(r"出入信息|出入记录|门禁|通行记录")),
)

_EXPORT_INTENT_RE = re.compile(r"导出|下载报表|下载文件|export", re.IGNORECASE)


@dataclass(frozen=True)
class ExportResourceDecision:
    """导出 resource 裁决结果。"""

    resource: str | None = None
    need_choice: bool = False
    candidates: tuple[str, ...] = field(default_factory=tuple)
    reason: str = ""


def match_explicit_export_resource(message: str) -> str | None:
    """本句含导出专名时返回 resource；否则 None（不做默认告警）。"""
    text = message or ""
    if _SENTRY_HANDOVER_RE.search(text):
        return "sentry_handover"
    if _DUTY_INFO_RE.search(text):
        return "duty_info"
    if _DUTY_MANAGE_RE.search(text):
        return "duty_manage"
    if _ACS_RECORD_RE.search(text):
        return "acs_record"
    if _ALARM_EXPORT_RE.search(text) and _EXPORT_INTENT_RE.search(text):
        return "alarm_report"
    if _ALARM_EXPORT_RE.search(text) and not _EXPORT_INTENT_RE.search(text):
        # 「查告警」等非导出句：不当作显式导出类型，留给上下文软信号
        return None
    if re.search(r"导出.{0,6}(告警|报警)|(告警|报警).{0,6}导出", text):
        return "alarm_report"
    return None


def collect_context_export_resources(*texts: str) -> list[str]:
    """从若干文本中收集出现过的导出相关业务域（去重、保序）。"""
    found: list[str] = []
    seen: set[str] = set()
    for raw in texts:
        text = (raw or "").strip()
        if not text:
            continue
        explicit = match_explicit_export_resource(text)
        if explicit and explicit not in seen:
            seen.add(explicit)
            found.append(explicit)
            continue
        for resource, pattern in _CONTEXT_DOMAIN_PATTERNS:
            if resource in seen:
                continue
            if pattern.search(text):
                seen.add(resource)
                found.append(resource)
    return found


def resolve_export_resource(
    current_message: str,
    *,
    recent_messages: list[str] | None = None,
) -> ExportResourceDecision:
    """
    结合本轮话与会话上下文裁决 download_file.resource。

    规则（与产品策略一致）:
    1. 本句专名明确 → 直接采用
    2. 上下文仅命中一个相关业务域 → 采用该域
    3. 否则 need_choice：候选为上下文命中的域；若无命中则列出全部支持类型
    """
    current = (current_message or "").strip()
    recent = [m.strip() for m in (recent_messages or []) if m and str(m).strip()]

    explicit = match_explicit_export_resource(current)
    if explicit:
        return ExportResourceDecision(
            resource=explicit,
            need_choice=False,
            candidates=(explicit,),
            reason="explicit_current",
        )

    context_hits = collect_context_export_resources(current, *recent)
    if len(context_hits) == 1:
        only = context_hits[0]
        return ExportResourceDecision(
            resource=only,
            need_choice=False,
            candidates=(only,),
            reason="unique_context",
        )

    if len(context_hits) > 1:
        return ExportResourceDecision(
            resource=None,
            need_choice=True,
            candidates=tuple(context_hits),
            reason="ambiguous_context",
        )

    # 无业务域信号：若本句像导出意图或为空（依赖上下文的工具重调），列出全部类型
    return ExportResourceDecision(
        resource=None,
        need_choice=True,
        candidates=tuple(SUPPORTED_EXPORT_RESOURCES),
        reason="no_context",
    )


def infer_download_resource(message: str, recent_messages: list[str] | None = None) -> str:
    """
    兼容旧调用：能唯一裁决则返回 resource。

    歧义时仍返回 ``alarm_report``（仅用于 Plan 步骤文案等展示兜底），
    **执行路径请用** ``resolve_export_resource``，勿把歧义默认当执行参数。
    """
    decision = resolve_export_resource(message, recent_messages=recent_messages)
    if decision.resource:
        return decision.resource
    return "alarm_report"


def export_resource_select_field(candidates: list[str] | tuple[str, ...]) -> dict:
    """构造 ask_params 用的导出类型下拉字段。"""
    opts = []
    for key in candidates:
        label = EXPORT_RESOURCE_LABELS.get(key, key)
        opts.append({"label": label, "value": key})
    if not opts:
        opts = [
            {"label": EXPORT_RESOURCE_LABELS[k], "value": k} for k in SUPPORTED_EXPORT_RESOURCES
        ]
    return {
        "name": "resource",
        "label": "导出类型",
        "type": "select",
        "required": True,
        "description": "请选择要导出的业务类型",
        "options": opts,
    }


def stamp_export_resource_confirmed(
    merged_args: dict,
    hitl_payload: dict | None,
) -> dict:
    """若 HITL 表单含 resource 且用户已填，则打确认标记（防歧义清空死循环）。"""
    from typing import Any

    out: dict[str, Any] = dict(merged_args)
    if not isinstance(hitl_payload, dict):
        return out
    field_names = {
        str(f.get("name") or "") for f in (hitl_payload.get("fields") or []) if isinstance(f, dict)
    }
    if "resource" in field_names and str(out.get("resource") or "").strip():
        out[EXPORT_RESOURCE_CONFIRMED_KEY] = True
    return out
