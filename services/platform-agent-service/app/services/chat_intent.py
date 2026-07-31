"""
纯对话意图识别（Phase C1）。

文件职责
--------
判断用户本轮消息是否「只需聊天、不必调工具」：
寒暄、道谢、能力咨询等 → 父图 ``chat_direct`` 短路，避免模型空跑 tool call；
含告警 / 导出 / 导航等业务词 → 返回 False，走正常 Plan / ReAct。

在 Agent 流程中的位置
--------------------
    stream_chat 组装上下文之前或 classify 阶段
      → is_chat_only_message(user_message)
      → True：父图 chat_direct（create_agent tools=[]）
      → False：继续 plan_confirm / device_gate / react

白话解释
--------
值班员说「你好」时，没必要先建 Plan 再查工具；
若说「你好，帮我查告警」，虽有寒暄，但带了业务词，就必须当业务处理。

如何被调用
----------
- 主要：application.conversation.chat / classify 相关节点
- 输入：用户原始消息字符串
- 输出：bool（是否可走纯对话短路）
"""

from __future__ import annotations

import re

# 一旦出现则视为「需工具 / 业务操作」，不可走纯对话短路
_TOOL_INTENT_PATTERN = re.compile(
    r"告警|报警|导出|下载|打开|跳转|导航|查询|查一下|查下|查下|统计|确认|批量|"
    r"excel|报表|列表|详情|设备|管理|页面|路径|"
    r"开门|关门|开锁|播报|广播|下发指令|指令下发|下发命令|命令下发|远程开门|"
    r"近\d|近[一二三四五六七八九十两]|"
    r"今天|昨天|本周|本月|上周|上月|"
    r"\d+\s*分钟|\d+\s*小时|\d+\s*天",
    re.IGNORECASE,
)

# 纯对话常见句式（全文或子串匹配）
_CHAT_ONLY_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"^(你好|您好|hi|hello|hey|嗨|早上好|下午好|晚上好)[!！?？\.。\s]*$",
        re.IGNORECASE,
    ),
    re.compile(r"^(谢谢|感谢|thanks|thank you)[!！?？\.。\s]*$", re.IGNORECASE),
    re.compile(r"^(再见|拜拜|bye)[!！?？\.。\s]*$", re.IGNORECASE),
    re.compile(r"^(好的|知道了|明白|ok|okay)[!！?？\.。\s]*$", re.IGNORECASE),
    re.compile(r"你(能|可以).{0,8}什么"),  # 你能帮我做什么 / 你能做什么
    re.compile(r"有什么(功能|能力)"),
    re.compile(r"你是谁|你是什么|介绍一下你自己"),
    re.compile(r"(怎么|如何)使用|使用说明|功能介绍|帮助文档"),
)


def is_chat_only_message(message: str) -> bool:
    """
    判断是否可走纯对话短路（不调工具）。

    判定顺序（白话）
    ----------------
    1. 空消息 → 否
    2. 命中业务/工具关键词（含「你好，帮我查告警」）→ 否
    3. 匹配寒暄 / 能力咨询等句式 → 是
    4. 其余模糊句 → 否（交给后续路由，避免误短路）

    参数
    ----
    message : str
        用户本轮输入原文。

    返回
    ----
    bool
        True 表示可走父图 ``chat_direct``；False 表示需业务图处理。
    """
    text = (message or "").strip()
    if not text:
        return False
    # 业务词优先：混合寒暄 + 查告警 必须走工具路径
    if _TOOL_INTENT_PATTERN.search(text):
        return False
    return any(pat.search(text) for pat in _CHAT_ONLY_PATTERNS)
