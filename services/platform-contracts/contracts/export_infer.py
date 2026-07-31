"""导出 resource 推断与 preflight 共用常量（无平台 HTTP 副作用）。"""

from __future__ import annotations

import re

# 与告警查询页 TransferModal 一致：平台 exportAlarm 单次 size 上限
EXPORT_ALARM_BATCH_MAX = 30000

# 仅时间范围筛选的非告警导出（preflight 共用时间 HITL）
TIME_ONLY_EXPORT_RESOURCES = frozenset(
    {"sentry_handover", "duty_info", "duty_manage", "acs_record"}
)

# 从用户原话推断 download_file.resource（专名优先于默认告警）
_SENTRY_HANDOVER_RE = re.compile(r"岗哨交接|哨位交接|岗哨.{0,8}交接|交接.{0,8}岗哨")
_DUTY_INFO_RE = re.compile(r"值班信息")
_DUTY_MANAGE_RE = re.compile(r"值班管理")
_ACS_RECORD_RE = re.compile(r"出入信息|出入记录|门禁.{0,6}记录|通行记录")


def infer_download_resource(message: str) -> str:
    """根据用户原话推断导出 resource；默认 alarm_report。"""
    text = message or ""
    if _SENTRY_HANDOVER_RE.search(text):
        return "sentry_handover"
    if _DUTY_INFO_RE.search(text):
        return "duty_info"
    if _DUTY_MANAGE_RE.search(text):
        return "duty_manage"
    if _ACS_RECORD_RE.search(text):
        return "acs_record"
    return "alarm_report"
