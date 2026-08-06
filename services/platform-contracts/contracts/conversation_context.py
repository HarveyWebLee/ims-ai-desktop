"""
通用会话轮次上下文（全工具共享，非某一工具专用）。

职责
----
- 从 ContextVar 读取本轮原话 + 近期用户句
- 识别代词/短追问，供 Prompt 组装提示（不改写工具执行参数）
- 合并前后端近期用户句

原则
----
工具空槽补参由大模型完成；缺参由 preflight HITL 询问。
本模块不再用正则/焦点静默改写 tool args。
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


def enrich_tool_args_from_conversation(
    tool_name: str,
    args: dict[str, Any] | None,
    *,
    turn: TurnContext | None = None,
) -> dict[str, Any]:
    """
    历史兼容：不再按会话正则/焦点改写工具空槽。

    补参由大模型在 tool_call 时完成；缺参由 preflight HITL 询问用户。
    ``tool_name`` / ``turn`` 保留仅为调用方签名兼容，不参与推断。
    """
    _ = (tool_name, turn)
    return dict(args or {})


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
