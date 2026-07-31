"""Platform MCP 工具注册表（唯一业务工具清单）。"""

from __future__ import annotations

from langchain_core.tools import BaseTool

from platform_mcp.runtime.tools.alarm import (
    batch_confirm_alarms,
    batch_process_alarms,
    get_alarm_detail,
    query_alarms,
)
from platform_mcp.runtime.tools.client_actions import (
    navigate_to,
    open_alarm_detail,
    open_device_detail,
    pause,
)
from platform_mcp.runtime.tools.device import (
    get_device_detail,
    query_device_variable_history,
    query_device_variable_realtime,
    query_device_variables,
    query_devices,
    send_device_cmd,
)
from platform_mcp.runtime.tools.export import download_file

PLATFORM_TOOL_NAMES: tuple[str, ...] = (
    "navigate_to",
    "pause",
    "open_alarm_detail",
    "query_alarms",
    "get_alarm_detail",
    "download_file",
    "batch_confirm_alarms",
    "batch_process_alarms",
    "query_devices",
    "get_device_detail",
    "query_device_variables",
    "query_device_variable_realtime",
    "query_device_variable_history",
    "send_device_cmd",
    "open_device_detail",
)


def get_platform_tools() -> list[BaseTool]:
    """返回可注册到 FastMCP 的 LangChain Tools。"""
    return [
        navigate_to,
        pause,
        open_alarm_detail,
        query_alarms,
        get_alarm_detail,
        download_file,
        batch_confirm_alarms,
        batch_process_alarms,
        query_devices,
        get_device_detail,
        query_device_variables,
        query_device_variable_realtime,
        query_device_variable_history,
        send_device_cmd,
        open_device_detail,
    ]
