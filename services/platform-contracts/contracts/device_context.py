"""
会话内设备指称消解（纯文本，不调平台 API）。

用途
----
多轮对话中用户说「给它下发指令 / 给这台开门」时，从本轮 + 近期用户句
抽出可交给 resolve_device_command 的 device_name / device_code 线索。
"""

from __future__ import annotations

import re

# 代词 / 回指：本轮未点名设备，须回看近期消息或工具结果焦点
_DEVICE_PRONOUN_RE = re.compile(
    r"(它|它们|该设备|这台设备|这个设备|这台|这个|那个|上述设备|上面的?设备|"
    r"刚才的?设备|同一个设备|同一台|上述)"
)

# 设备名/编码捕获：字母编码、数字开头中文名、纯中文、其它编码（勿用 \\w 吞中文）
_DEVICE_TOKEN_CAPTURE = (
    r"(?:"
    r"[A-Za-z][A-Za-z0-9_.\-]{1,63}"
    r"|[0-9]+[\u4e00-\u9fff][\u4e00-\u9fffA-Za-z0-9_.\-]{0,36}"
    r"|[\u4e00-\u9fff][\u4e00-\u9fffA-Za-z0-9_.\-]{1,40}"
    r"|[A-Za-z0-9][A-Za-z0-9_.\-]{2,63}"
    r")"
)

# 「给/向/对 XXX 播放|开门|下发…」
_CONTROL_DEVICE_RE = re.compile(
    rf"(?:给|向|对)\s*({_DEVICE_TOKEN_CAPTURE})"
    r"(?:\s*(?:播放|播报|广播|开门|关门|下发|发指令|控制|写变量|指令))"
)

# 查询/查看类：须带查询动词，避免「给设备下发」误抽
_QUERY_DEVICE_RE = re.compile(
    rf"(?:查询|查看|查一下|查下|获取)\s*"
    rf"(?:设备|门禁)?\s*"
    rf"({_DEVICE_TOKEN_CAPTURE})"
    r"(?:\s*(?:的)?(?:设备|门禁|详情|状态|信息|变量))?"
)

# 名称后括号内编码：502多联机主机（502_DLJ） / 东大门(ANDUN_DEVICE_BH_001)
_PAREN_CODE_RE = re.compile(
    r"([\u4e00-\u9fff0-9][\u4e00-\u9fffA-Za-z0-9_.\-]{0,40})?\s*[（(]\s*"
    r"([A-Za-z0-9][A-Za-z0-9_.\-]{1,63})\s*[）)]"
)

# 显式槽位：设备编码 XXX / device_code=XXX
_EXPLICIT_SLOT_RE = re.compile(
    r"(?:设备编码|设备代码|device[_ ]?code|deviceCode)\s*[为是:=：]?\s*"
    r"[「『\"'“]?([A-Za-z0-9][A-Za-z0-9_.\-]{1,63})[」』\"'”]?",
    re.IGNORECASE,
)
_EXPLICIT_NAME_RE = re.compile(
    r"(?:设备名称|设备名|device[_ ]?name|deviceName)\s*[为是:=：]?\s*"
    r"[「『\"'“]?([\u4e00-\u9fffA-Za-z0-9][\u4e00-\u9fffA-Za-z0-9_.\-]{0,40})[」』\"'”]?",
    re.IGNORECASE,
)

# 过泛、不可作设备名的停用词
_STOP_TOKENS = frozenset(
    {
        "设备",
        "门禁",
        "详情",
        "状态",
        "信息",
        "变量",
        "指令",
        "命令",
        "控制",
        "下发",
        "广播",
        "播报",
        "开门",
        "关门",
        "全部",
        "所有",
        "列表",
        "一下",
        "这个",
        "那个",
        "这个设备",
        "那台设备",
        "什么",
        "哪些",
        "如何",
        "怎么",
        "设备下发",
        "设备指令",
        "设备控制",
    }
)


def message_has_device_pronoun(message: str) -> bool:
    """本轮是否用代词回指设备（它/这台/上述…）。"""
    return bool(_DEVICE_PRONOUN_RE.search(message or ""))


def _clean_token(raw: str | None) -> str | None:
    token = (raw or "").strip().strip("「」『』\"'“”[]【】")
    if not token or token in _STOP_TOKENS:
        return None
    if _DEVICE_PRONOUN_RE.fullmatch(token):
        return None
    if len(token) < 2:
        return None
    # 拒绝「目前在线的设备列表」这类查询范围描述，避免当成设备名
    if re.search(r"列表|目前|在线的|离线的|全部设备|所有设备|设备列表", token):
        return None
    return token


def extract_device_token_from_text(message: str) -> str | None:
    """
    从单句文本弱解析设备名或编码。

    优先级：显式槽位 → 括号编码 → 给/向/对 控制句 → 查询句。
    优先返回括号内编码（更利于 resolve_device_code）。
    """
    text = (message or "").strip()
    if not text:
        return None

    m = _EXPLICIT_SLOT_RE.search(text)
    if m:
        return _clean_token(m.group(1))

    m = _EXPLICIT_NAME_RE.search(text)
    if m:
        return _clean_token(m.group(1))

    m = _PAREN_CODE_RE.search(text)
    if m:
        code = _clean_token(m.group(2))
        if code:
            return code
        return _clean_token(m.group(1))

    m = _CONTROL_DEVICE_RE.search(text)
    if m:
        return _clean_token(m.group(1))

    m = _QUERY_DEVICE_RE.search(text)
    if m:
        return _clean_token(m.group(1))

    return None


def infer_device_token_from_conversation(
    message: str,
    recent_user_messages: list[str] | tuple[str, ...] | None = None,
) -> str | None:
    """
    结合本轮、近期用户句与（可选）工具结果设备焦点推断目标设备。

    - 本轮已点名且无代词回指 → 直接用本轮
    - 本轮为代词回指 → 优先唯一工具焦点，再扫近期用户句
    - 本轮未点名 → 扫近期，再退回焦点
    """
    current = (message or "").strip()
    current_token = extract_device_token_from_text(current)
    if current_token and not message_has_device_pronoun(current):
        return current_token

    def _unique_focus_token() -> str | None:
        try:
            from contracts.context import current_device_focus

            focus = current_device_focus.get()
            if focus is not None and getattr(focus, "is_unique", False):
                code = str(getattr(focus, "device_code", "") or "").strip()
                name = str(getattr(focus, "device_name", "") or "").strip()
                if code or name:
                    return code or name
        except Exception:  # noqa: BLE001
            return None
        return None

    # 代词续说：先用工具结果唯一焦点，避免近期「查在线设备列表」误抽
    if message_has_device_pronoun(current):
        focused = _unique_focus_token()
        if focused:
            return focused

    prior = [str(m).strip() for m in (recent_user_messages or ()) if m and str(m).strip()]
    for prior_msg in reversed(prior):
        found = extract_device_token_from_text(prior_msg)
        if found:
            return found

    focused = _unique_focus_token()
    if focused:
        return focused

    return current_token
