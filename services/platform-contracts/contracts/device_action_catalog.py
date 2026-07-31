"""
设备控制口语动作目录加载器。

文件职责
--------
从 JSON 加载「口语动作 → 变量提示 / 默认写入值」映射，供设备指令消解使用。
例如用户说「开门」，目录可提示应找门控相关变量，并推断写入值 open；
「播报」硬绑定 play，且写入值必须为播报正文（requireUserValue）。

数据源
------
``app/data/device_action_catalog.json``
与 ``packages/agent-core/device-action-catalog.ts`` 同步（前端/契约侧同源概念）。
开门/关门：``requiredVarName: status_door_control``；播报：``requiredVarName: play``。

在 Agent 流程中的位置
--------------------
    LLM / HITL 抽出 action 槽位（如「开门」「播报」）
      → find_device_action_hint / infer_value_from_action / extract_user_value_from_text
      → device_command_resolver 拼出 device_code + varName + value
      → send_device_cmd 下发

如何被调用
----------
- 主要消费者：``contracts.device_command_resolver``
- 也可被工具层在缺参推断时直接 import
- 加载结果进程内 ``lru_cache``，改 JSON 需重启进程才生效
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from contracts.paths import mcp_data_dir

# 共享 data：device_action_catalog.json（路径由 runtime_bind / 环境变量解析）


def _catalog_path() -> Path:
    return mcp_data_dir() / "device_action_catalog.json"


# 从口语中抽取播报/内容型写入值（按优先级尝试）
_USER_VALUE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?:下发)?广播(?:播报)?[：:\s]+(.+)$"),
    re.compile(r"播报(?:内容)?[：:\s]+(.+)$"),
    re.compile(r"广播(.+?)内容"),
    re.compile(r"播报(.+)$"),
    re.compile(r"(?:下发)?广播(.+)$"),
)


@lru_cache(maxsize=1)
def load_device_action_catalog() -> list[dict[str, Any]]:
    """
    加载动作目录 JSON（进程内只读一次）。

    返回
    ----
    list[dict]
        动作定义列表；文件缺失或根节点非数组时返回空列表。
    """
    if not _catalog_path().is_file():
        return []
    raw = _catalog_path().read_text(encoding="utf-8")
    data = json.loads(raw)
    return data if isinstance(data, list) else []


def find_device_action_hint(token: str) -> dict[str, Any] | None:
    """
    按口语 token 查找动作定义。

    匹配优先级（白话）
    ------------------
    1. ``action`` 字段精确等于 token
    2. ``aliases`` 别名精确等于 token
    3. token 包含某 action / 别名（宽松包含匹配）

    参数
    ----
    token : str
        如「开门」「关」「open」「播报」。

    返回
    ----
    dict | None
        命中的目录项（含 variableHints、valueHints 等）；未命中 None。
    """
    t = (token or "").strip()
    if not t:
        return None

    catalog = load_device_action_catalog()
    # 第一轮：精确匹配（避免「开门」误打到「开」的包含匹配过早返回）
    for hint in catalog:
        if str(hint.get("action") or "") == t:
            return hint
        aliases = hint.get("aliases") or []
        if any(str(a) == t for a in aliases):
            return hint

    # 第二轮：包含匹配（用户多打了几个字时仍能命中）
    for hint in catalog:
        action = str(hint.get("action") or "")
        aliases = [str(a) for a in (hint.get("aliases") or [])]
        if action and action in t:
            return hint
        if any(a in t for a in aliases if a):
            return hint
    return None


def action_requires_user_value(action_token: str) -> bool:
    """动作是否要求使用者明确给出写入值（如播报正文）。"""
    hint = find_device_action_hint(action_token)
    return bool(hint and hint.get("requireUserValue"))


def extract_user_value_from_text(action_token: str, *, user_text: str = "") -> str | None:
    """
    从口语中抽取 requireUserValue 类动作的写入正文。

    例如「播报请注意安全」→「请注意安全」；「广播紧急疏散内容」→「紧急疏散」。
    抽不到或仅剩动作词本身时返回 None（交给 HITL）。
    """
    if not action_requires_user_value(action_token):
        return None

    # 分别匹配原话与 action，避免拼接导致「播报正文 播报」重复
    candidates: list[str] = []
    for part in (user_text, action_token):
        text = str(part or "").strip()
        if text and text not in candidates:
            candidates.append(text)
    if not candidates:
        return None

    hint = find_device_action_hint(action_token)
    action_name = str((hint or {}).get("action") or "").strip()
    aliases = [str(a).strip() for a in ((hint or {}).get("aliases") or []) if str(a).strip()]
    noise = {action_name, *aliases, "内容"}

    for combined in candidates:
        for pattern in _USER_VALUE_PATTERNS:
            matched = pattern.search(combined)
            if not matched:
                continue
            content = str(matched.group(1) or "").strip()
            content = content.strip("「」\"'：:，,。.;； ")
            if not content or content in noise:
                continue
            return content
    return None


def infer_value_from_action(action_token: str, *, user_text: str = "") -> str | None:
    """
    根据动作目录推断默认写入值。

    白话解释
    --------
    「开门」通常对应 valueHints.open；「关门」对应 close；
    ``requireUserValue`` 动作（如播报）不推断，返回 None；
    说不清开/关时退回 default。``user_text`` 可带整句上下文帮助区分。

    参数
    ----
    action_token : str
        动作口语或目录中的 action 名。
    user_text : str
        用户原话（可选），用于区分 open / close 子键。

    返回
    ----
    str | None
        推断出的写入值；目录无条目、requireUserValue 或无可用 hint 时 None。
    """
    hint = find_device_action_hint(action_token)
    if not hint:
        return None
    if hint.get("requireUserValue"):
        return None

    value_hints = hint.get("valueHints") or {}
    if not isinstance(value_hints, dict):
        return None

    combined = f"{action_token} {user_text}".strip()
    close_keywords = ("关", "锁门", "停止", "close", "关闭")
    open_keywords = ("开", "打开", "启动", "open", "开启", "开锁")

    # 先判「关」再判「开」，避免「开关门」类歧义句优先落到 open
    if any(kw in combined for kw in close_keywords):
        close_val = value_hints.get("close")
        if close_val is not None and str(close_val).strip():
            return str(close_val)
    if any(kw in combined for kw in open_keywords):
        open_val = value_hints.get("open")
        if open_val is not None and str(open_val).strip():
            return str(open_val)

    default = value_hints.get("default")
    return str(default) if default is not None and str(default).strip() else None
