"""
Client Tools 模块：返回 client_action 供前端 ClientToolExecutor 执行

文件职责
--------
提供「不调平台业务 API、只指挥浏览器」的 LangChain 工具：
导航页面、等待 N 秒、打开告警/设备相关 UI。

白话概念
--------
Server Tool = 后端帮你查库改状态；
Client Tool = 后端只给一张「纸条」：请跳到这个路由 / 打开这个弹窗，
真正点菜单是浏览器（带用户登录态）完成的。

在 Agent 流程中的位置
--------------------
  LLM 选中 navigate_to / pause / open_*
    → tool_result(..., client_action={...})
    → SSE tool_end → 前端 ClientToolExecutor 执行

如何被调用
----------
- 经 ``registry.get_agent_tools()`` 绑定到图
- 导航多候选时内部 ``ask_user_params`` HITL 消歧

工具一览
--------
- navigate_to：模糊匹配菜单后跳转（可能 HITL 选页）
- pause：客户端计时等待
- open_alarm_detail：打开告警详情弹窗
- open_device_detail：跳转设备管理并带 deviceCode
"""

from __future__ import annotations

# @tool 装饰器：将普通函数注册为 LangChain 可调用的 Tool
from langchain_core.tools import tool

from platform_mcp.runtime.hitl import ask_user_params  # 多候选时让用户选择

# 导航路由匹配服务：根据用户口语化描述查找平台页面路径
from platform_mcp.runtime.navigation_routes import (
    format_match_option_label,  # 格式化候选项展示文案
    pick_navigation_path,  # 模糊匹配，返回唯一路径或候选列表
    resolve_navigation_path,  # 纠正/规范化 path（如 groupId 错误）
)
from platform_mcp.runtime.result import tool_result  # 统一 JSON 返回格式


def _disambiguate_navigation_path(user_query: str, candidates: list) -> str:
    """
    当模糊匹配得到多个候选页面时，通过 HITL 表单让用户选择目标 path。

    参数：
        user_query: 用户原始描述（如「设备管理」）
        candidates: 匹配到的路由对象列表（含 path、name 等属性）

    返回：
        用户选中的 originPath 字符串

    异常：
        ValueError — 用户未选择任何项
    """
    # 最多展示 10 个候选项，避免表单过长
    options = [{"label": format_match_option_label(m), "value": m.path} for m in candidates[:10]]
    merged = ask_user_params(
        tool="navigate_to",
        message=(
            f"找到 {len(candidates)} 个与「{user_query}」匹配的页面，"
            "请确认要跳转的目标（按匹配度排序）："
        ),
        fields=[
            {
                "name": "path",
                "label": "目标页面",
                "type": "select",  # 下拉选择框
                "required": True,
                "options": options,
            }
        ],
        current={},
    )
    selected = merged.get("path")
    if not selected:
        raise ValueError("未选择目标页面")
    return str(selected)


@tool
def navigate_to(path: str, query: dict | None = None) -> str:
    """
    帮使用者跳转到平台指定页面（Client Tool）。

    参数
    ----
    path : str
        使用者原话（如「设施管理」）或完整 originPath。
    query : dict | None
        可选 URL 查询参数。

    HITL
    ----
    模糊匹配多名候选 → ask_user_params 选择 path。

    返回（ToolResult JSON）
    ----------------------
    client_action={action:navigate, path, query?}；前端 history 跳转。

    LLM 应直接调用，禁止先用自然语言追问页面名称。
    """
    from platform_mcp.runtime.tool_preflight import ensure_tool_args

    try:
        merged = ensure_tool_args("navigate_to", {"path": path, "query": query or {}})
    except ValueError as exc:
        return tool_result(ok=False, summary=str(exc))

    user_query = str(merged.get("path") or "").strip()
    query = merged.get("query") if isinstance(merged.get("query"), dict) else query
    if not user_query:
        return tool_result(ok=False, summary="请说明要跳转的页面名称或路径")

    # pick_navigation_path 返回 (唯一路径或 None, 候选列表)
    resolved, candidates = pick_navigation_path(user_query)

    # 多个候选：interrupt 让用户选
    if resolved is None and candidates:
        try:
            resolved = _disambiguate_navigation_path(user_query, candidates)
        except ValueError as exc:
            return tool_result(ok=False, summary=str(exc))

    if not resolved:
        return tool_result(
            ok=False,
            summary=(
                f"未找到与「{user_query}」匹配的平台页面。"
                "请尝试更具体的菜单名称（如「设施管理」或「设备管理」）。"
            ),
        )

    # 若 LLM 直接传了含错误 groupId 的 URL，尝试纠正
    resolved = resolve_navigation_path(resolved)

    # 构造前端 navigate 动作
    action: dict = {"action": "navigate", "path": resolved}
    if query:
        action["query"] = query

    # 从候选中取匹配到的菜单名，用于友好摘要
    matched_name = next(
        (m.name for m in candidates if m.path == resolved),
        user_query,
    )
    return tool_result(
        ok=True,
        summary=f"已为您跳转到「{matched_name}」",
        client_action=action,
    )


@tool
def pause(seconds: int = 1) -> str:
    """
    在继续下一步前等待指定秒数（Client Tool）。

    参数
    ----
    seconds : int
        等待秒数，内部钳制到 0～120。

    返回
    ----
    client_action={action:pause, seconds}；由浏览器计时，不阻塞 Agent 后端。
    """
    sec = max(0, min(int(seconds), 120))
    return tool_result(
        ok=True,
        summary=f"已等待 {sec} 秒",
        client_action={"action": "pause", "seconds": sec},
    )


@tool
def open_alarm_detail(alarm_id: str) -> str:
    """
    帮使用者在当前页面打开告警详情弹窗（Client Tool）。

    参数
    ----
    alarm_id : str
        告警业务编号。

    返回
    ----
    client_action={action:openModal, modal:alarmDetail, params:{alarmId}}。
    通常可与 get_alarm_detail（Server）配合；本工具本身不调平台 API。
    """
    return tool_result(
        ok=True,
        summary=f"已打开告警 {alarm_id} 的详情弹窗",
        client_action={
            "action": "openModal",
            "modal": "alarmDetail",
            "params": {"alarmId": alarm_id},
        },
    )


@tool
def open_device_detail(device_code: str, device_name: str = "") -> str:
    """
    帮使用者在平台内打开设备管理页面并定位到指定设备（Client Tool）。

    参数
    ----
    device_code : str
        设备编码（必填，可由 preflight 补全）。
    device_name : str
        可选，仅用于友好 summary。

    返回
    ----
    client_action navigate 到设备管理页，query 带 deviceCode。
    """
    from platform_mcp.runtime.tool_preflight import ensure_tool_args

    try:
        merged = ensure_tool_args(
            "open_device_detail",
            {"device_code": device_code, "device_name": device_name},
        )
    except ValueError as exc:
        return tool_result(ok=False, summary=str(exc))

    code = str(merged.get("device_code") or "").strip()
    if not code:
        return tool_result(ok=False, summary="请提供设备编码。")

    display = str(merged.get("device_name") or "").strip() or code
    return tool_result(
        ok=True,
        summary=f"已为您打开设备「{display}」的管理页面",
        client_action={
            "action": "navigate",
            "path": "/config_management/config/equipment_manage",
            "query": {"deviceCode": code},
        },
    )
