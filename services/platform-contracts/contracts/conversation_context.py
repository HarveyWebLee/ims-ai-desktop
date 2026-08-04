"""
通用会话轮次上下文（全工具共享，非某一工具专用）。

职责
----
- 从 ContextVar 读取本轮原话 + 近期用户句
- 对「空槽位」做弱推断补全（不覆盖模型已填值）
- 识别代词/短追问，供 Prompt 与 preflight 共用

原则
----
上下文能唯一补全 → 写入参数；不能唯一确定 → 保持空，交给领域 HITL。
禁止「无条件留空弹表」压过已明确的多轮信息。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

# 通用回指：它/这个/上述/刚才/继续/再…
_FOLLOWUP_PRONOUN_RE = re.compile(
    r"(它|它们|该|这台|这个|那个|上述|上面|刚才|此前|之前|同一|继续|再[次帮]?|"
    r"还是|同样|同一个|同一台|同上)"
)
_SHORT_FOLLOWUP_RE = re.compile(
    r"^(下发|导出|下载|开门|关门|播报|广播|确认|处理|查询?变量|查详情|打开详情|"
    r"批量确认|批量处理|再来一次|继续|好的|可以|执行|开始)[\s。.!！？?]*$",
)


@dataclass(frozen=True)
class TurnContext:
    """单次工具调用可见的会话文本上下文。"""

    utterance: str = ""
    recent: tuple[str, ...] = ()

    def texts_newest_first(self) -> list[str]:
        """本轮优先，再从近到远扫近期句。"""
        out: list[str] = []
        if self.utterance.strip():
            out.append(self.utterance.strip())
        for msg in reversed(self.recent):
            text = str(msg or "").strip()
            if text and text not in out:
                out.append(text)
        return out


def load_turn_context() -> TurnContext:
    """从请求 ContextVar 加载本轮上下文（无 ContextVar 时返回空）。"""
    from contracts.context import current_recent_user_messages, current_user_utterance

    utterance = (current_user_utterance.get() or "").strip()
    recent = tuple(
        str(m).strip() for m in (current_recent_user_messages.get() or ()) if m and str(m).strip()
    )
    return TurnContext(utterance=utterance, recent=recent)


def is_contextual_followup(message: str) -> bool:
    """本轮是否像依赖上文的短追问 / 代词续说。"""
    text = (message or "").strip()
    if not text:
        return False
    if _FOLLOWUP_PRONOUN_RE.search(text):
        return True
    if len(text) <= 24 and _SHORT_FOLLOWUP_RE.match(text):
        return True
    return False


def _has_text(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict)):
        return len(value) > 0
    return True


def _fill_if_empty(args: dict[str, Any], key: str, value: str | None) -> None:
    if not value or not str(value).strip():
        return
    if _has_text(args.get(key)):
        return
    args[key] = str(value).strip()


def _load_alarm_focus() -> Any | None:
    try:
        from contracts.context import current_alarm_focus

        return current_alarm_focus.get()
    except Exception:  # noqa: BLE001
        return None


def _apply_alarm_focus_to_args(name: str, data: dict[str, Any]) -> None:
    """用 checkpoint 告警焦点补空槽（时间/状态/设备/编号）；不覆盖已填值。"""
    focus = _load_alarm_focus()
    if focus is None:
        return

    alarm_filter_tools = {
        "query_alarms",
        "download_file",
        "batch_confirm_alarms",
        "batch_process_alarms",
    }
    detail_tools = {"get_alarm_detail", "open_alarm_detail"}

    if name in alarm_filter_tools:
        if not _has_text(data.get("start_time")) and not _has_text(data.get("end_time")):
            _fill_if_empty(data, "start_time", getattr(focus, "start_time", "") or "")
            _fill_if_empty(data, "end_time", getattr(focus, "end_time", "") or "")
        _fill_if_empty(data, "status", getattr(focus, "status", "") or "")
        if not _has_text(data.get("device_code")) and not _has_text(data.get("device_name")):
            _fill_if_empty(data, "device_code", getattr(focus, "device_code", "") or "")
            _fill_if_empty(data, "device_name", getattr(focus, "device_name", "") or "")
        if not _has_text(data.get("alarm_category_id")):
            cats = list(getattr(focus, "alarm_category_id", None) or [])
            if cats:
                data["alarm_category_id"] = cats
        if not _has_text(data.get("alarm_rank_id")):
            ranks = list(getattr(focus, "alarm_rank_id", None) or [])
            if ranks:
                data["alarm_rank_id"] = ranks
        # 唯一告警 + 批量写：可直接带 alarm_ids，跳过再查列表
        if name in {"batch_confirm_alarms", "batch_process_alarms"} and getattr(
            focus, "is_unique_alarm", False
        ):
            _fill_if_empty(data, "alarm_ids", getattr(focus, "alarm_id", "") or "")

    if name in detail_tools and getattr(focus, "is_unique_alarm", False):
        _fill_if_empty(data, "alarm_id", getattr(focus, "alarm_id", "") or "")


def enrich_tool_args_from_conversation(
    tool_name: str,
    args: dict[str, Any] | None,
    *,
    turn: TurnContext | None = None,
) -> dict[str, Any]:
    """
    按会话上下文补全**空**槽位；已有值绝不覆盖。

    覆盖常见跨工具槽位：device_name / device_code、start_time / end_time、
    告警 status / alarm_id（含 checkpoint 工具结果焦点）。
    领域专属裁决（导出 resource 等）仍由各自 preflight 负责。
    """
    data = dict(args or {})
    ctx = turn or load_turn_context()
    texts = ctx.texts_newest_first()
    name = (tool_name or "").strip()

    # ── 设备名/编码：凡接受这些字段的工具均可受益 ──
    if not _has_text(data.get("device_code")) and not _has_text(data.get("device_name")):
        from contracts.device_context import infer_device_token_from_conversation

        inferred = infer_device_token_from_conversation(ctx.utterance, ctx.recent)
        if not inferred:
            # 直接读焦点（代词句且用户句无线索时）
            try:
                from contracts.context import current_device_focus

                focus = current_device_focus.get()
                if focus is not None and getattr(focus, "is_unique", False):
                    inferred = str(
                        getattr(focus, "device_code", "") or getattr(focus, "device_name", "") or ""
                    ).strip()
            except Exception:  # noqa: BLE001
                inferred = None
        if inferred:
            # 编码形态优先塞 device_code，否则 device_name
            if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.\-]{1,63}", inferred) and re.search(
                r"[A-Za-z_]", inferred
            ):
                _fill_if_empty(data, "device_code", inferred)
            else:
                _fill_if_empty(data, "device_name", inferred)

    # ── 时间范围：优先用户句相对时间，再回落 checkpoint 告警焦点 ──
    time_tools = {
        "query_alarms",
        "download_file",
        "batch_confirm_alarms",
        "batch_process_alarms",
        "query_device_variable_history",
    }
    if (
        name in time_tools
        and not _has_text(data.get("start_time"))
        and not _has_text(data.get("end_time"))
        and texts
    ):
        from contracts.time_range import extract_alarm_time_range_from_message

        for text in texts:
            start, end = extract_alarm_time_range_from_message(text)
            if start or end:
                _fill_if_empty(data, "start_time", start)
                _fill_if_empty(data, "end_time", end)
                break

    # ── 告警焦点：补用户句未覆盖的时间/状态/编号等 ──
    _apply_alarm_focus_to_args(name, data)

    return data


def merge_recent_user_messages(
    *,
    frontend_recent: list[str] | tuple[str, ...] | None,
    server_recent: list[str] | tuple[str, ...] | None,
    current_message: str,
    limit: int = 5,
) -> list[str]:
    """
    合并前端与服务端近期用户句（去重、排除本轮），供 assemble / ContextVar 使用。

    服务端 session_store 在页面刷新后仍有记录，避免仅依赖前端 Store。
    """
    current = (current_message or "").strip()
    merged: list[str] = []
    seen: set[str] = set()
    for raw in list(frontend_recent or ()) + list(server_recent or ()):
        text = str(raw or "").strip()
        if not text or text == current or text in seen:
            continue
        seen.add(text)
        merged.append(text)
    if limit > 0:
        return merged[-limit:]
    return merged
