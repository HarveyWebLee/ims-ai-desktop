"""
Prompt 组装服务 —— 将静态 Markdown 与运行时上下文拼成 LLM 可用的提示词。

文件职责
--------
拼装 system prompt（角色 + 工具表 + API 摘要 + 时间/路由）与
LLM 可见的 user message（页面路径 + 近期消息 + 本轮原话）。

在 Agent 流程中的位置
--------------------
位于「图执行层」与「LLM 模型层」之间：
  builder.stream_chat / chat_direct
    → build_system_prompt / build_chat_direct_system_prompt
    → build_llm_user_message（含 resolve_recent_messages_for_intent）
  历史回显：thread_history → extract_user_display_message（剥掉 Prompt 外壳）

如何被调用
----------
- 主 Agent：``build_system_prompt`` + ``build_llm_user_message``
- 纯对话短路：``build_chat_direct_system_prompt``
- 工具表：``format_registered_tools_bindings``（转调 tool_catalog_loader）

白话解释
--------
给模型发工牌和任务单：system 说「你是谁、能按哪些按钮」；
user 说「用户现在在哪页、刚刚说过什么、这一句原话是啥」。

依赖：
    - app/prompts/*.md、navigation_routes、platform_api_catalog、utils/time_range
"""

# from __future__ import annotations 让类型注解可以引用尚未定义的类名（Python 3.7+ 特性）
from __future__ import annotations

# ── 标准库 ──
import re
from pathlib import Path  # 跨平台路径操作
from typing import Any  # 任意类型的类型注解占位符

# prompts 目录：与本文件同级目录的上级下的 prompts 文件夹
# Path(__file__) 是当前 .py 文件的绝对路径；.resolve() 消除符号链接；.parent 取父目录
_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def _read_prompt_file(name: str, fallback: str = "") -> str:
    """
    读取 prompts 目录下的 Markdown 文件内容。

    参数:
        name: 文件名，如 "system.md"
        fallback: 文件不存在时返回的默认字符串

    返回:
        文件 UTF-8 文本内容，或 fallback
    """
    path = _PROMPTS_DIR / name  # / 运算符拼接路径（Path 对象支持）
    if path.exists():  # 判断文件是否存在
        return path.read_text(encoding="utf-8")  # 一次性读入全部文本
    return fallback


def format_registered_tools_bindings() -> str:
    """
    生成「已注册工具 ↔ 平台接口」Markdown 表格，注入 system prompt。

    数据来源: app/tools/catalog.json（export 自 tool-catalog.ts）。
    """
    from contracts.tool_catalog_loader import (
        format_registered_tools_bindings as _from_catalog,
    )

    return _from_catalog()


def format_alarm_api_compact() -> str:
    """
    从 platform_api_index 注入告警域高频接口摘要（非全量 swagger）。

    业务含义:
        供 LLM 理解 query/export/confirm 与平台 path 的对应关系，
        避免在 prompt 中塞入 14 万行的 swaggerApi.json。

    返回:
        Markdown 摘要块；无数据时返回空字符串
    """
    # 延迟导入：仅在需要时才加载 platform_api_catalog，减少模块启动开销
    from contracts.platform_api_catalog import format_api_for_prompt, list_apis_by_tag

    # 优先精确 path，避免 tag 下列出过多无关接口
    preferred_paths = (
        ("/alarm/getAlarmList", "POST"),
        ("/alarm/exportAlarm", "GET"),
        ("/alarm/confirmAlarm", "POST"),
    )
    from contracts.platform_api_catalog import get_api

    apis: list[dict[str, Any]] = []  # 类型注解：元素为 dict 的列表
    for path, method in preferred_paths:
        api = get_api(path, method)
        if api:
            apis.append(api)

    # 精确 path 未命中时，按 tag 兜底取前 4 条
    if not apis:
        apis = list_apis_by_tag("alarmManagementApi")[:4]  # [:4] 切片取前 4 个

    if not apis:
        return ""

    lines = ["### 告警域 API 参考（摘要）", ""]
    # 生成器表达式：对每个 api 调用 format_api_for_prompt，结果 extend 进 lines
    lines.extend(format_api_for_prompt(a) for a in apis)
    return "\n".join(lines)


def format_request_context(
    *,
    metadata: dict[str, Any] | None = None,
    recent_user_messages: list[str] | None = None,
) -> str:
    """
    将单次请求的页面路径、近期消息格式化为 Prompt 片段（不含当前时间）。

    参数:
        metadata: 前端传来的上下文，如 {"current_path": "/config/..."}
        recent_user_messages: 近期用户消息列表，供多轮理解

    返回:
        Markdown 片段；无有效信息时返回空字符串

    注意:
        参数前的 * 表示后面必须用「关键字传参」，如 format_request_context(metadata=...)
    """
    lines: list[str] = []
    # (metadata or {})：metadata 为 None 时用空 dict，避免 .get 报错
    path = str((metadata or {}).get("current_path") or "").strip()
    if path:
        lines.append(f"- **使用者当前页面路径**：`{path}`")

    # 列表推导式：过滤空消息并 strip 首尾空白
    prior = [m.strip() for m in (recent_user_messages or []) if m and m.strip()]
    if prior:
        lines.append("- **近期用户消息（供多轮理解，当前消息以最后一条为准）**：")
        for msg in prior[-5:]:  # 只取最近 5 条
            lines.append(f"  - {msg}")

    if not lines:
        return ""
    return "## 本请求上下文\n\n" + "\n".join(lines)


# 与 build_llm_user_message 拼接格式一致；历史还原时用于剥离 Prompt 上下文
USER_TURN_SECTION_HEADER = "## 使用者本轮消息"

# 意图冲突检测：导航类新请求 vs 近期导出类消息
_EXPORT_INTENT_RE = re.compile(r"导出|下载|报表|报警|告警|excel", re.IGNORECASE)
_NAV_INTENT_RE = re.compile(r"打开|跳转|导航|去|进入|值班|页面", re.IGNORECASE)

# 设备控制：具体动作 + 通用「下发指令」—— 强制立即 tool call，禁止自然语言追问设备
_DEVICE_CONTROL_SPECIFIC_ACTION_RE = re.compile(
    r"开门|关门|开锁|远程开门|开闸|关闸|锁门|"
    r"播报|广播|下发广播|广播播报|语音播报|播放广播|广播通知"
)
# 通用下发：未点名开门/播报时仍走 send_device_cmd + HITL 选设备/变量（任意可写变量）
# 「指令下发」与「下发指令」同义（产品文案常见词序倒置）
_DEVICE_CONTROL_GENERIC_RE = re.compile(
    r"下发指令|指令下发|下发命令|命令下发|发送指令|发指令|设备指令|控制设备|远程控制|"
    r"写变量|写入变量|给设备.{0,16}(指令|命令|控制)"
)
_DEVICE_CONTROL_ACTION_RE = re.compile(
    rf"(?:{_DEVICE_CONTROL_SPECIFIC_ACTION_RE.pattern})|"
    rf"(?:{_DEVICE_CONTROL_GENERIC_RE.pattern})"
)

# 条件分支 / 先查后控：含「开门」但主意图不是纯控制，禁止强制 send_device_cmd
_CONDITIONAL_OR_INSPECT_THEN_CONTROL_RE = re.compile(
    r"(如果|若|要是).{0,32}(在线|离线)|"
    # 「在线开门 / 离线查…」口语（可不含「就/则/才」）
    r"(在线|离线).{0,12}(开门|关门|播报|下发|查看|查询|查历史|查变量)|"
    r"(在线|离线).{0,16}(就|则|才).{0,32}(开门|关门|播报|下发|查看|查询)|"
    # 「查…门禁/设备 … 在线…离线…」
    r"(查看|查询|先查|查).{0,48}(门禁|设备|状态|详情|是否在线).{0,64}"
    r"(在线|离线|如果|若|开门|关门|播报|下发|历史)|"
    r"(开门|关门|播报|下发).{0,48}(如果|若).{0,32}(离线|在线|不在线)"
)


def _is_conditional_or_inspect_then_control(message: str) -> bool:
    """是否为「先查状态再分支控制」类需求（不应强制立即 send_device_cmd）。"""
    return bool(_CONDITIONAL_OR_INSPECT_THEN_CONTROL_RE.search(message or ""))


def parse_device_control_action(message: str) -> str | None:
    """
    从用户原话解析设备控制动作。

    返回
    ----
    None
        非纯控制意图（或条件先查后控）。
    ""
        通用下发指令（未指定开门/关门/播报等具体动作）。
    非空 str
        标准动作名（开门 / 关门 / 播报）。
    """
    text = (message or "").strip()
    if not text or not _DEVICE_CONTROL_ACTION_RE.search(text):
        return None
    if _is_conditional_or_inspect_then_control(text):
        return None

    if re.search(r"关门|锁门|关闸|关闭门禁", text):
        return "关门"
    if re.search(r"播报|广播", text):
        return "播报"
    if re.search(r"开门|开锁|远程开门|开闸|开启门禁", text):
        return "开门"
    # 仅命中通用「下发指令」等：不默认开门，交由 HITL 选变量
    if _DEVICE_CONTROL_GENERIC_RE.search(text):
        return ""
    return None


def build_device_control_intent_note(message: str) -> str | None:
    """
    设备控制意图：前置提示强制立即调用 send_device_cmd。

    防止模型用自然语言追问「哪台设备」、把能力收窄为仅开门/播报，
    或未 tool call 却声称「已下发 / 正在等待执行结果」。
    条件句（如在线开门/离线查历史）不注入，避免压制 get_device_detail 等查询步骤。
    """
    action = parse_device_control_action(message)
    if action is None:
        return None

    text = (message or "").strip()
    param_hints: list[str] = []
    device_token = _extract_device_token_from_control_message(text)
    if device_token:
        param_hints.append(f'原话已点名设备，请传 `device_name` 或 `device_code`="{device_token}"')
    broadcast_body = _extract_broadcast_content(text) if action == "播报" else None
    if broadcast_body:
        param_hints.append(f'播报正文请传 `variable_value`="{broadcast_body}"')

    param_line = ("；".join(param_hints) + "。") if param_hints else ""
    anti_hallucination = (
        "**禁止**在尚未收到工具返回前用自然语言声称「已下发 / 已播报 / 正在等待执行结果」；"
        "须先完成 `send_device_cmd` tool call，再根据工具结果总结。"
    )

    if action:
        device_clause = (
            "若原话未指明设备，请将 `device_code`/`device_name` 留空，"
            "由系统弹出可筛选设备表格供单选。"
            if not device_token
            else ""
        )
        return (
            "## 重要提示\n\n"
            f"本轮为设备控制意图（{action}）。**必须立即**调用工具 `send_device_cmd`，"
            f'至少传入 `action="{action}"`。'
            f"{param_line}"
            f"{device_clause}"
            "**禁止**仅用自然语言追问设备名称或设备编码。"
            f"{anti_hallucination}"
        )

    return (
        "## 重要提示\n\n"
        "本轮为设备控制/下发指令意图（未指定具体动作）。"
        "**必须立即**调用工具 `send_device_cmd`，"
        "可将 `action`/`device_code`/`device_name`/`variable_name`/`variable_value` 留空；"
        "由系统弹出设备表格，并按可写变量渐进补参。"
        "支持**任意具备可写变量的设备**（不限于门禁开门/关门或广播播报）。"
        "**禁止**仅用自然语言追问设备或把能力限定为开门/关门/播报；"
        "**禁止**用闲聊代替工具调用。"
        f"{anti_hallucination}"
    )


def _extract_device_token_from_control_message(message: str) -> str | None:
    """从「给 XXX 播放/开门」等说法中抽出设备名/编码（弱解析，仅作提示）。"""
    text = (message or "").strip()
    if not text:
        return None
    match = re.search(
        r"(?:给|向|对)\s*([A-Za-z0-9][\w.\-]{1,63}|[\u4e00-\u9fff][\u4e00-\u9fff\w.\-]{0,31})"
        r"(?:\s*(?:播放|播报|广播|开门|关门|下发|发指令|控制))",
        text,
    )
    if match:
        return match.group(1).strip()
    return None


def _extract_broadcast_content(message: str) -> str | None:
    """从「内容为XXX / 播报XXX」抽出播报正文。"""
    text = (message or "").strip()
    if not text:
        return None
    match = re.search(
        r"(?:内容为|播报内容为|广播内容为)\s*[「『\"'“]?(.+?)[」』\"'”]?\s*$",
        text,
    )
    if match:
        body = match.group(1).strip().strip("「」『』\"'“”")
        return body or None
    return None


def resolve_recent_messages_for_intent(
    current_message: str,
    recent_user_messages: list[str] | None,
) -> tuple[list[str], str | None]:
    """
    当本轮意图与近期消息冲突时，剔除误导性近期消息并返回附加说明。

    典型场景：用户取消导出后说「打开值班」，近期消息仍含「导出近一天报警」，
    会导致 LLM 再次调用 download_file。
    """
    prior = [m.strip() for m in (recent_user_messages or []) if m and m.strip()]
    current = (current_message or "").strip()
    if not prior or not current:
        return prior, None

    current_is_nav = bool(_NAV_INTENT_RE.search(current)) and not bool(
        _EXPORT_INTENT_RE.search(current)
    )
    if not current_is_nav:
        return prior, None

    last_prior = prior[-1]
    if not _EXPORT_INTENT_RE.search(last_prior):
        return prior, None

    note = (
        "## 重要提示\n\n"
        "上一轮「导出/下载告警」相关操作已被使用者取消，请勿再次调用 `download_file`。"
        "请仅处理本轮使用者的新需求。"
    )
    if len(prior) <= 1:
        return [], note
    filtered = [m for m in prior if not _EXPORT_INTENT_RE.search(m)]
    return filtered, note


def extract_user_display_message(text: str) -> str:
    """
    从 Checkpoint HumanMessage 中还原使用者可见的原始输入。

    LangGraph 持久化的是 build_llm_user_message 的完整字符串；
    前端气泡与 recent_user_messages 应只展示/传递本轮用户原话。
    """
    raw = text.strip()
    if not raw:
        return raw
    marker = USER_TURN_SECTION_HEADER
    if marker in raw:
        body = raw.split(marker, 1)[1].strip()
        return body or raw
    return raw


def build_llm_user_message(
    message: str,
    *,
    metadata: dict[str, Any] | None = None,
    recent_user_messages: list[str] | None = None,
) -> str:
    """
    合并页面路径、近期消息与本轮输入，供 LLM 意图识别使用。

    参数:
        message: 用户本轮原始输入
        metadata: 页面上下文
        recent_user_messages: 近期用户消息

    返回:
        完整 user message 字符串（可能含「本请求上下文」+「使用者本轮消息」两段）
    """
    ctx = format_request_context(
        metadata=metadata,
        recent_user_messages=recent_user_messages,
    )
    body = message.strip()
    if ctx:
        return f"{ctx}\n\n{USER_TURN_SECTION_HEADER}\n\n{body}"
    return body


def build_system_prompt(
    *,
    metadata: dict[str, Any] | None = None,
    recent_user_messages: list[str] | None = None,
) -> str:
    """
    构建完整 system prompt（Agent 初始化用，通常不含单次请求 metadata）。

    结构:
        system.md → intent_and_tools.md → 工具/API 摘要 → 运行时（时间+导航）

    参数:
        metadata: 可选，测试时可注入请求上下文
        recent_user_messages: 可选，测试时可注入近期消息

    返回:
        拼接后的 system prompt 全文
    """
    from contracts.navigation_routes import (
        format_navigation_hints_for_prompt,
        get_navigation_rules_for_prompt,
    )
    from contracts.time_range import format_reference_hint

    base = _read_prompt_file("system.md", "你是综合信息平台智能助手。")
    intent = _read_prompt_file("intent_and_tools.md", "")
    # summarize.md 已合并入 response_style.md，注入主 Agent 回复结构规范
    response_style = _read_prompt_file("response_style.md", "")
    tools_bindings = format_registered_tools_bindings()
    alarm_api = format_alarm_api_compact()
    now_hint = format_reference_hint()
    route_rules = get_navigation_rules_for_prompt()
    route_hints = format_navigation_hints_for_prompt()

    # Agent 级 system prompt 不重复注入单次请求上下文（由 build_llm_user_message 负责）
    runtime_parts = [
        "## 运行时上下文",
        "",
        f"- **当前时间（Asia/Shanghai）**：{now_hint}",
        "- 相对时间以该时刻为基准；推荐将使用者原话传入 start_time。",
        route_rules,
        "### 常用页面路由（navigate_to 优先使用下列 originPath）",
        "",
        route_hints,
    ]

    parts = [
        base,
        intent,
        response_style,
        tools_bindings,
        alarm_api,
        "\n".join(runtime_parts),
    ]
    # 若调用方显式传入 metadata（如测试），可附加请求上下文
    request_ctx = format_request_context(
        metadata=metadata,
        recent_user_messages=recent_user_messages,
    )
    if request_ctx:
        parts.append(request_ctx)

    # 过滤掉空片段后，用双换行拼接
    return "\n\n".join(p for p in parts if p.strip())


def build_chat_direct_system_prompt() -> str:
    """
    纯对话短路专用 system prompt（Phase C1）。

    不含工具绑定与 intent_and_tools，避免模型误触发 tool call。
    仍注入当前时间与常用路由，便于回答「你能做什么」类问题。
    """
    from contracts.navigation_routes import format_navigation_hints_for_prompt
    from contracts.time_range import format_reference_hint

    base = _read_prompt_file("chat_direct.md", "你是综合信息平台智能助手。")
    now_hint = format_reference_hint()
    route_hints = format_navigation_hints_for_prompt()

    runtime = "\n".join(
        [
            "## 运行时上下文",
            "",
            f"- **当前时间（Asia/Shanghai）**：{now_hint}",
            "### 常用页面（介绍能力时可引用）",
            "",
            route_hints,
        ]
    )
    return "\n\n".join(p for p in [base, runtime] if p.strip())
