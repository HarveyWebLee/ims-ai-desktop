"""
统一 Tool 返回结构模块（ToolResult → JSON 字符串）

文件职责
--------
所有 @tool 函数最终都应 ``return tool_result(...)``。
LangChain 要求工具返回 str；本模块把结构化结果序列化为 JSON。
权威 TypeScript 契约：``packages/shared-types`` 的 ``ToolResult``
（含 ``client_action`` / ``client_actions``）；见 ``docs/architecture/06-contracts.md``。

白话概念
--------
工具干完活要交一份「作业纸」给 LLM 和前端：
- ok / summary：LLM 用来写下一句回复
- data：Workspace / 详情卡片用结构化数据
- client_action(s)：浏览器执行 navigate / download / openModal 等
- user_cancelled：用户点了拒绝，编排层勿自动重试

在 Agent 流程中的位置
--------------------
  Server/Client Tool 执行完毕
    → tool_result(...)
    → SSE tool_end.result（前端 parser + LLM 可见）

如何被调用
----------
  return tool_result(ok=True, summary="共 5 条告警", data={...})
"""

from __future__ import annotations

import json  # 将 Python 字典序列化为 JSON 字符串
from typing import Any  # Any 表示任意类型，用于 data 等泛型参数


def tool_result(
    *,
    ok: bool,
    summary: str,
    data: Any = None,
    client_action: dict[str, Any] | None = None,
    client_actions: list[dict[str, Any]] | None = None,
    user_cancelled: bool = False,
) -> str:
    """
    构造并序列化工具执行结果（统一 ToolResult 契约）。

    参数（均为关键字参数）
    --------------------
    ok : bool
        是否业务成功；用户 HITL 拒绝时一般为 False。
    summary : str
        给 LLM / 侧栏看的中文摘要（必填）。
    data : Any
        可选结构化载荷（列表、计数、错误详情等）。
    client_action : dict | None
        单条前端动作（navigate / download / openModal / refresh / pause…）。
    client_actions : list | None
        多条前端动作；与 client_action 二选一，本函数优先写 client_actions。
    user_cancelled : bool
        True=用户主动取消，编排层应跳过自动重试。

    返回
    ----
    JSON 字符串，例如 ``{"ok": true, "summary": "共 5 条告警", "data": {...}}``。
    ensure_ascii=False，中文不转义。
    """
    # 基础字段：成功与否 + 人类可读摘要
    payload: dict[str, Any] = {"ok": ok, "summary": summary}
    if user_cancelled:
        payload["user_cancelled"] = True
    # 有数据时才加入 data 键，减少 JSON 体积
    if data is not None:
        payload["data"] = data
    # client_actions 优先：分批导出等多文件下载场景
    if client_actions:
        payload["client_actions"] = client_actions
    elif client_action:
        payload["client_action"] = client_action
    # ensure_ascii=False 保证中文不被转义为 \\uXXXX
    return json.dumps(payload, ensure_ascii=False)
