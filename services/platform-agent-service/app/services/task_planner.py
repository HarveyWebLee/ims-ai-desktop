"""
多步任务计划与 Re-plan 辅助服务。

文件职责
--------
1. 用规则从用户中文原话「猜」出多步 Plan（查询→导出、导航→停留等）
2. 工具失败后生成恢复计划（Re-plan）与失败原因文案
3. 解析工具返回 JSON 的 ok / summary / user_cancelled

在 Agent 流程中的位置
--------------------
偏「规划辅助」层（主意图识别已由 LLM + PlanTracker 承担）：
  复合任务兜底 / envelope → build_task_plan / build_single_step_direct_plan
  工具失败重试 → build_replan_after_failure（经 retry_policy 调用）
  观察 tool_end → parse_tool_result / parse_tool_result_ok

如何被调用
----------
- ``retry_policy.run_with_replan_retry`` → ``build_replan_after_failure`` / ``parse_tool_result``
- plan / envelope 相关路径 → ``build_task_plan``、``is_compound_query_export``

白话解释
--------
像「行程单生成器」：看见「先查告警再导出」就写成两步待办；
某步失败时，把失败步标红、未做的跳过，再追加「重试某某」步骤。
注意：主流程不再靠本模块识别意图，但 Re-plan 与复合兜底仍需要它。

相关模块:
    - plan_executor / agent_tool_retry / stream_envelope.PlanTracker
"""

from __future__ import annotations

# ── 标准库 ──
import re  # 正则表达式，用于从用户话术中匹配关键词
from typing import Any

# ── 模块级正则常量（编译一次，多次复用，比每次 re.search 传字符串更高效）──
# 显式复合：多子句连接词（不含裸「并」，避免「查询…并导出，然后…」被误切）
_COMPOUND_RE = re.compile(r"然后|接着|再|之后|并且|最后")
# 同句内「查询并导出」连词（仅用于 is_compound_query_export 等判断，不用于子句切分）
_INLINE_AND_RE = re.compile(r"并(?![用])")
_ALARM_RE = re.compile(r"告警|报警|警报")
_QUERY_RE = re.compile(r"查|查询|统计|多少|几条|列表|情况|看看")
_EXPORT_RE = re.compile(r"导出|下载|excel|xlsx|报表文件", re.I)  # re.I = 忽略大小写
_NAV_RE = re.compile(r"打开|跳转|导航|进入|去(?![哪])")
# 复合子句内的停留指令，如「停留10s」
_PAUSE_RE = re.compile(r"停留\s*(\d+)\s*s", re.I)
# 告警状态口语（与 alarm.py _parse_alarm_list_scope 对齐）
_STATUS_UNPROCESSED_RE = re.compile(r"未处理")
_STATUS_PENDING_RE = re.compile(r"待确认|未确认")
_STATUS_PROCESSED_RE = re.compile(r"已处理")
_STATUS_CONFIRMED_RE = re.compile(r"已确认")
# 批量写操作口语（与 alarm.py batch_* 工具对齐）
_BATCH_CONFIRM_RE = re.compile(r"批量确认")
_BATCH_PROCESS_RE = re.compile(r"批量处理")


def extract_alarm_status_from_message(message: str) -> str:
    """
    从用户原话提取告警状态筛选词（供 Plan 预填 query_alarms / download_file）。

    返回:
        空字符串表示未限定状态；否则为「未处理」「待确认」「已确认」「已处理」之一。
    """
    msg = (message or "").strip()
    if not msg:
        return ""
    # 先匹配「已处理」，避免「未处理」被误拆（二者不含重叠，顺序仍按 specificity）
    if _STATUS_UNPROCESSED_RE.search(msg):
        return "未处理"
    if _STATUS_PENDING_RE.search(msg):
        return "待确认"
    if _STATUS_PROCESSED_RE.search(msg):
        return "已处理"
    if _STATUS_CONFIRMED_RE.search(msg):
        return "已确认"
    return ""


def _alarm_query_step_label(message: str) -> str:
    """带状态限定的查询步骤标签。"""
    status = extract_alarm_status_from_message(message)
    return f"查询{status}告警" if status else "查询告警数据"


# download_file 各 resource 的步骤标签（非告警）
_DOWNLOAD_RESOURCE_LABELS: dict[str, str] = {
    "sentry_handover": "导出岗哨交接记录",
    "duty_info": "导出值班信息",
    "duty_manage": "导出值班管理",
    "acs_record": "导出出入信息",
}


def _resolve_download_resource(
    *,
    user_message: str,
    original_steps: list[dict[str, Any]] | None = None,
    failed_args: dict[str, Any] | None = None,
) -> str:
    """从 failed_args、原计划步骤或用户原话推断 download_file.resource。"""
    from contracts.export_infer import infer_download_resource

    if failed_args:
        resource = failed_args.get("resource")
        if resource:
            return str(resource)
    if original_steps:
        for step in reversed(original_steps):
            if step.get("tool") != "download_file":
                continue
            params = step.get("params") or {}
            if isinstance(params, dict) and params.get("resource"):
                return str(params["resource"])
            break
    return infer_download_resource(user_message)


def download_export_step_label(
    user_message: str,
    *,
    resource: str | None = None,
    retry: bool = False,
) -> str:
    """
    生成 download_file 步骤标签（Plan / Re-plan TaskProgress 展示）。

    参数:
        user_message: 用户原话（推断 resource 与告警状态）
        resource: 显式 resource；缺省时从原话/步骤/failed_args 推断
        retry: True 时前缀「重试」，如「重试导出值班管理」
    """
    res = resource or _resolve_download_resource(user_message=user_message)
    if res == "alarm_report":
        status = extract_alarm_status_from_message(user_message)
        base = f"导出{status}告警报表" if status else "导出告警报表"
    else:
        base = _DOWNLOAD_RESOURCE_LABELS.get(res, "导出报表")
    return f"重试{base}" if retry else base


def _alarm_export_step_label(message: str) -> str:
    """导出步骤标签（告警 / 各业务报表）。"""
    return download_export_step_label(message)


def _infer_tool(text: str) -> str | None:
    """
    从单个子句文本推断应调用的主要工具名。

    参数:
        text: 用户话术的一个片段（如「导出告警报表」）

    返回:
        工具名字符串（如 "download_file"），无法推断时返回 None
    """
    # 批量写操作优先于导出/查询（避免「批量处理」子句被误解析）
    if _BATCH_CONFIRM_RE.search(text):
        return "batch_confirm_alarms"
    if _BATCH_PROCESS_RE.search(text):
        return "batch_process_alarms"
    if _EXPORT_RE.search(text):
        return "download_file"
    if _QUERY_RE.search(text) and _ALARM_RE.search(text):
        return "query_alarms"
    if _NAV_RE.search(text):
        return "navigate_to"
    if _ALARM_RE.search(text) and re.search(r"详情|编号", text):
        return "get_alarm_detail"
    return None


def _infer_label(text: str) -> str:
    """
    从子句生成使用者可读的步骤描述（TaskProgress UI 展示用）。

    参数:
        text: 用户话术片段

    返回:
        中文步骤标签，如「查询告警数据」「跳转到设备管理」
    """
    tool = _infer_tool(text)
    # 三元表达式：条件为真取前者，否则取后者
    snippet = text[:24] + ("…" if len(text) > 24 else "")
    if tool == "download_file":
        return _alarm_export_step_label(text)
    if tool == "query_alarms":
        return _alarm_query_step_label(text)
    if tool == "batch_confirm_alarms":
        status = extract_alarm_status_from_message(text)
        return f"批量确认{status}告警" if status else "批量确认告警"
    if tool == "batch_process_alarms":
        status = extract_alarm_status_from_message(text)
        return f"批量处理{status}告警" if status else "批量处理告警"
    if tool == "navigate_to":
        m = re.search(r"(?:打开|跳转(?:到)?|导航(?:到)?|进入)\s*(.+)", text)
        target = m.group(1).strip() if m else snippet
        if target.startswith("到"):
            target = target[1:].strip()
        return f"跳转到{target[:16]}"
    if tool == "get_alarm_detail":
        return "查看告警详情"
    return snippet or "执行操作"


def _expand_alarm_query_export_steps(part: str) -> list[dict[str, Any]]:
    """子句内同时含查询+导出时展开为两步（避免 _infer_tool 仅命中 export）。"""
    if not (_ALARM_RE.search(part) and _QUERY_RE.search(part) and _EXPORT_RE.search(part)):
        return []
    return [
        {
            "label": _alarm_query_step_label(part),
            "tool": "query_alarms",
            "status": "pending",
        },
        {
            "label": _alarm_export_step_label(part),
            "tool": "download_file",
            "status": "pending",
        },
    ]


def _expand_compound_part_to_steps(part: str) -> list[dict[str, Any]]:
    """
    将复合任务子句展开为 Plan 步骤。

    导航子句若含「停留 Ns」，拆为 navigate_to + pause 两步，便于 TaskProgress 展示与执行。
    """
    part = (part or "").strip()
    if not part:
        return []

    # 单个子句内「查询…并导出」须拆成 query + download 两步
    query_export_steps = _expand_alarm_query_export_steps(part)
    if query_export_steps:
        return query_export_steps

    tool = _infer_tool(part)
    if not tool:
        return []

    pause_m = _PAUSE_RE.search(part)
    if tool == "navigate_to" and pause_m:
        steps: list[dict[str, Any]] = []
        nav_text = _PAUSE_RE.sub("", part).strip().rstrip("，,。 ")
        if nav_text:
            steps.append(
                {
                    "label": _infer_label(nav_text),
                    "tool": "navigate_to",
                    "status": "pending",
                }
            )
        seconds = int(pause_m.group(1))
        steps.append(
            {
                "label": f"停留 {seconds} 秒",
                "tool": "pause",
                "status": "pending",
                "params": {"seconds": seconds},
            }
        )
        return steps

    return [
        {
            "label": _infer_label(part),
            "tool": tool,
            "status": "pending",
        }
    ]


def build_task_plan(
    message: str,
    *,
    metadata: dict[str, Any] | None = None,
) -> list[dict[str, Any]] | None:
    """
    根据用户消息用规则生成多步计划（非 LLM 路径）。

    参数:
        message: 用户完整输入
        metadata: 可选页面上下文，如 current_path

    返回:
        步骤列表，每步为 dict(id, label, tool, status)；
        单步任务返回 None（前端不展示 TaskProgress）
    """
    msg = message.strip()
    if not msg:
        return None

    steps: list[dict[str, Any]] = []
    step_id = 1

    # bool(...) 将 match 对象转为 True/False：匹配成功为 True
    has_alarm = bool(_ALARM_RE.search(msg))
    has_query = bool(_QUERY_RE.search(msg))
    has_export = bool(_EXPORT_RE.search(msg))
    has_nav = bool(_NAV_RE.search(msg))
    has_batch_process = bool(_BATCH_PROCESS_RE.search(msg))
    has_batch_confirm = bool(_BATCH_CONFIRM_RE.search(msg))

    # ── 业务规则路径 A：显式复合「先…然后…再…」──
    # 必须先于隐式复合，否则「查询并导出」可能被两边各扩一次导致重复步骤
    if _COMPOUND_RE.search(msg):
        # split 按连接词切分，过滤空片段
        parts = [p.strip() for p in _COMPOUND_RE.split(msg) if p.strip()]
        if len(parts) >= 2:
            # 使用局部列表：切分后不足 2 个有效工具步时不得污染外层 steps，
            # 否则后续「隐式复合 查询+导出」会 append 到残留步骤上导致重复（如「查询并导出近三月告警」）。
            compound_steps: list[dict[str, Any]] = []
            for part in parts:
                for step in _expand_compound_part_to_steps(part):
                    step["id"] = str(len(compound_steps) + 1)
                    compound_steps.append(step)
            # 至少两步才算「多步 Plan」；单步应返回 None（前端不展示 TaskProgress）
            if len(compound_steps) >= 2:
                return compound_steps

    # ── 业务规则路径 B：隐式复合「同句里既有查又有导」──
    if has_alarm and has_query and has_export:
        steps.append(
            {
                "id": str(step_id),
                "label": _alarm_query_step_label(msg),
                "tool": "query_alarms",
                "status": "pending",
            }
        )
        step_id += 1
        steps.append(
            {
                "id": str(step_id),
                "label": _alarm_export_step_label(msg),
                "tool": "download_file",
                "status": "pending",
            }
        )
        step_id += 1
        if has_batch_process:
            status = extract_alarm_status_from_message(msg)
            steps.append(
                {
                    "id": str(step_id),
                    "label": f"批量处理{status}告警" if status else "批量处理告警",
                    "tool": "batch_process_alarms",
                    "status": "pending",
                }
            )
        elif has_batch_confirm:
            steps.append(
                {
                    "id": str(step_id),
                    "label": "批量确认告警",
                    "tool": "batch_confirm_alarms",
                    "status": "pending",
                }
            )
        return steps

    # ── 业务规则路径 C：查询 + 批量处理（无导出）──
    if has_alarm and has_query and has_batch_process and not has_export:
        steps.append(
            {
                "id": str(step_id),
                "label": _alarm_query_step_label(msg),
                "tool": "query_alarms",
                "status": "pending",
            }
        )
        step_id += 1
        steps.append(
            {
                "id": str(step_id),
                "label": _infer_label(msg),
                "tool": "batch_process_alarms",
                "status": "pending",
            }
        )
        return steps

    # ── 业务规则路径 D：导航 + 查询/导出 ──
    if has_nav and has_alarm and (has_query or has_export):
        nav_label = _infer_label(msg)
        steps.append(
            {
                "id": str(step_id),
                "label": nav_label if "跳转" in nav_label else "跳转到告警相关页面",
                "tool": "navigate_to",
                "status": "pending",
            }
        )
        step_id += 1
        if has_query:
            steps.append(
                {
                    "id": str(step_id),
                    "label": "查询告警数据",
                    "tool": "query_alarms",
                    "status": "pending",
                }
            )
            step_id += 1
        if has_export:
            steps.append(
                {
                    "id": str(step_id),
                    "label": _alarm_export_step_label(msg),
                    "tool": "download_file",
                    "status": "pending",
                }
            )
        return steps

    # ── 业务规则路径 E：人就在告警页 + 话术含查+导 → 默认两步 ──
    path = str((metadata or {}).get("current_path") or "")
    if "alarm" in path.lower() and has_query and has_export:
        return [
            {
                "id": "1",
                "label": "查询告警数据",
                "tool": "query_alarms",
                "status": "pending",
            },
            {
                "id": "2",
                "label": _alarm_export_step_label(msg),
                "tool": "download_file",
                "status": "pending",
            },
        ]

    return None


def build_single_step_direct_plan(
    message: str,
    *,
    metadata: dict[str, Any] | None = None,
) -> list[dict[str, Any]] | None:
    """
    单步告警直达（仅查询 / 仅导出）的计划。

    供 envelope 与 Re-plan 保留步骤上下文；复合任务返回 None（由 build_task_plan 处理）。

    参数:
        message: 用户输入
        metadata: 页面上下文（当前未使用，保留扩展）

    返回:
        单步计划列表，或 None
    """
    msg = message.strip()
    if not msg or is_compound_query_export(msg):
        return None

    has_alarm = bool(_ALARM_RE.search(msg))
    has_query = bool(_QUERY_RE.search(msg))
    has_export = bool(_EXPORT_RE.search(msg))

    if has_alarm and has_export and not has_query:
        return [
            {
                "id": "1",
                "label": _alarm_export_step_label(msg),
                "tool": "download_file",
                "status": "pending",
            }
        ]

    if has_alarm and has_query and not has_export:
        return [
            {
                "id": "1",
                "label": "查询告警数据",
                "tool": "query_alarms",
                "status": "pending",
            }
        ]

    return None


def is_compound_query_export(message: str) -> bool:
    """
    判断是否为「先查告警再导出」复合任务。

    参数:
        message: 用户输入

    返回:
        True 表示需要先查询再导出
    """
    msg = message.strip()
    if not (_ALARM_RE.search(msg) and _EXPORT_RE.search(msg)):
        return False
    if _QUERY_RE.search(msg):
        return True
    if _COMPOUND_RE.search(msg) or _INLINE_AND_RE.search(msg):
        parts = _COMPOUND_RE.split(msg)
        if not parts or parts == [msg]:
            parts = _INLINE_AND_RE.split(msg)
        # any(...) 只要有一个 part 匹配即为 True
        has_q = any(_QUERY_RE.search(p) for p in parts)
        has_e = any(_EXPORT_RE.search(p) for p in parts)
        return has_q and has_e
    return False


# 单轮对话最多 Re-plan 次数（含首次失败后的恢复计划）
MAX_REPLAN_ATTEMPTS = 1


def build_replan_after_failure(
    *,
    original_steps: list[dict[str, Any]],
    failed_tool: str,
    error_summary: str,
    user_message: str,
    failed_args: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], str]:
    """
    某步工具失败后生成恢复计划（Re-plan）。

    业务逻辑:
        1. 保留已完成步骤
        2. 将失败步标记 error，未执行步标记 skipped
        3. 追加 1～2 条可执行恢复步骤

    参数:
        original_steps: 原计划步骤列表
        failed_tool: 失败的工具名
        error_summary: 错误摘要（供 UI 展示）
        user_message: 用户原话（保留供后续 LLM 续跑）

    返回:
        (新步骤列表, 重新规划原因说明) 的元组
    """
    summary = (error_summary or "未知错误").strip()[:120]
    preserved: list[dict[str, Any]] = []
    for step in original_steps:
        st = dict(step)  # 浅拷贝，避免修改原 dict
        # 未执行的 pending 改为 skipped，避免 UI 仍显示「等待中」
        if st.get("status") == "pending":
            st["status"] = "skipped"
        preserved.append(st)

    recovery: list[dict[str, Any]] = []
    reason = ""

    # 按失败工具类型生成不同的恢复策略（查询失败时若原计划含导出，恢复计划也带导出）
    if failed_tool == "query_alarms":
        reason = f"查询告警失败：{summary}。将重试查询后再继续后续步骤。"
        recovery = [
            {
                "id": "replan-1",
                "label": "重试查询告警",
                "tool": "query_alarms",
                "status": "pending",
            },
        ]
        # 若原计划含导出步骤，恢复计划也追加导出
        if any(s.get("tool") == "download_file" for s in original_steps):
            export_label = download_export_step_label(
                user_message,
                resource=_resolve_download_resource(
                    user_message=user_message,
                    original_steps=original_steps,
                    failed_args=failed_args,
                ),
            )
            recovery.append(
                {
                    "id": "replan-2",
                    "label": export_label,
                    "tool": "download_file",
                    "status": "pending",
                }
            )
    elif failed_tool == "download_file":
        export_resource = _resolve_download_resource(
            user_message=user_message,
            original_steps=original_steps,
            failed_args=failed_args,
        )
        export_label = download_export_step_label(
            user_message,
            resource=export_resource,
            retry=True,
        )
        reason = f"导出失败：{summary}。将{export_label}。"
        recovery = [
            {
                "id": "replan-1",
                "label": export_label,
                "tool": "download_file",
                "status": "pending",
            },
        ]
    elif failed_tool == "navigate_to":
        reason = f"页面跳转失败：{summary}。将重试导航。"
        recovery = [
            {
                "id": "replan-1",
                "label": "重试页面跳转",
                "tool": "navigate_to",
                "status": "pending",
            },
        ]
    else:
        reason = f"步骤失败（{failed_tool}）：{summary}。请根据提示调整后重试。"
        recovery = [
            {
                "id": "replan-1",
                "label": "重试上一步操作",
                "tool": failed_tool or None,
                "status": "pending",
            },
        ]

    new_steps = preserved + recovery  # 列表拼接
    return new_steps, reason


# 这些错误码与 user_cancelled 一样：禁止自动重试 / Re-plan
_NON_RETRYABLE_ERROR_CODES = frozenset(
    {
        "tool_permission_denied",
        "authentication_required",
        "permission_context_missing",
    }
)


def parse_tool_result(result_str: str) -> tuple[bool, str, bool, bool]:
    """
    解析工具返回的 JSON 字符串。

    返回:
        (是否成功, 摘要文本, 是否应停止重试, 是否用户主动取消)

    说明:
        - stop_retry：user_cancelled / non_retryable / 权限类 error_code
        - user_cancelled：仅使用者主动取消；**不可**与 stop_retry 混用
          （否则 Plan 会把硬失败误标为 skipped）
    """
    import json

    try:
        data = json.loads(result_str)
        if isinstance(data, dict):
            ok = bool(data.get("ok", True))
            summary = str(data.get("summary") or "")
            user_cancelled = bool(data.get("user_cancelled"))
            error_code = ""
            nested_non_retryable = False
            nested = data.get("data")
            if isinstance(nested, dict):
                error_code = str(nested.get("error_code") or "")
                nested_non_retryable = bool(nested.get("non_retryable"))
            if not error_code:
                error_code = str(data.get("error_code") or "")
            stop_retry = (
                user_cancelled or nested_non_retryable or error_code in _NON_RETRYABLE_ERROR_CODES
            )
            return ok, summary, stop_retry, user_cancelled
    except json.JSONDecodeError, TypeError:
        pass
    return True, result_str[:200] if result_str else "", False, False


def parse_tool_result_ok(result_str: str) -> tuple[bool, str]:
    """
    解析工具返回的 JSON 字符串，提取成功标志与摘要。

    参数:
        result_str: 工具返回的 JSON 字符串，约定含 ok、summary 字段

    返回:
        (是否成功, 摘要文本) 元组；解析失败时默认 (True, 原文前 200 字)
    """
    ok, summary, _, _ = parse_tool_result(result_str)
    return ok, summary
