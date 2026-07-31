"""
平台 HTTP API 客户端模块（Server Tools 专用）

文件职责
--------
Agent 后端以「当前登录用户」身份调用综合信息平台 REST API：
拼 URL、带 JWT、解析 ``{ code, data, message }``，失败抛 ``PlatformApiError``。

白话概念
--------
Agent 自己没有告警库/设备库，真正干活的是平台后端。
本模块是「代用户打电话」的话务员：Token 从 context 取，业务数据从响应里取。

在 Agent 流程中的位置
--------------------
  alarm / device 等 Server Tool
    → call_platform_api(method, path, data)
    → settings.platform_api_base + path
    → 成功返回 body["data"]；code!=0 或网络问题 → PlatformApiError

如何被调用
----------
  data = call_platform_api(method="post", path="/alarm/getAlarmList", data=payload)

约定
----
- path 不含 ``/api/app`` 前缀（配置里已含）
- GET 的 data 作 query；POST 作 JSON body
- 必须已 set ``current_auth_token``，否则视为未登录
"""

from __future__ import annotations

from typing import Any  # 请求体、响应 data 等动态 JSON 结构

import httpx  # 现代 HTTP 客户端库，支持 sync/async，此处用同步 Client

from contracts.context import current_auth_token  # 当前请求的用户 JWT
from contracts.settings import settings  # 读取 PLATFORM_API_BASE 等环境配置


class PlatformApiError(Exception):
    """
    平台 API 业务或网络失败时抛出的自定义异常。

    属性：
        message: 错误说明（str，通过 Exception 基类传递）
        code: 平台返回的业务 code（非 0 时有值）
        data: 平台返回的 data 字段（可选，用于调试）
    """

    def __init__(self, message: str, code: int | None = None, data: Any = None):
        super().__init__(message)
        self.code = code
        self.data = data


def call_platform_api(
    *,
    method: str,
    path: str,
    data: dict[str, Any] | list[Any] | None = None,
    timeout: float = 30.0,
) -> Any:
    """
    调用综合信息平台 REST API。

    参数：
        method: HTTP 方法，"get" 或 "post"（大小写不敏感）
        path: API 路径，如 "/alarm/getAlarmList"（不含 /api/app 前缀）
        data: GET 时作为 query params，POST 时作为 JSON body
        timeout: 请求超时秒数，默认 30 秒

    返回：
        成功时返回 body["data"]（平台业务数据）

    异常：
        PlatformApiError — 未登录、HTTP 错误、code!=0 等
    """
    # 从上下文变量读取 JWT；middleware 在请求入口已 set
    token = current_auth_token.get()
    if not token:
        raise PlatformApiError("未登录或缺少 Authorization，无法调用平台 API")

    # 拼接完整 URL，例如 http://192.168.x.x:18001/api/app/alarm/getAlarmList
    url = f"{settings.platform_api_base.rstrip('/')}{path}"
    headers = {"Authorization": token, "Content-Type": "application/json"}

    # with 语句确保 Client 用完后关闭连接
    with httpx.Client(timeout=timeout) as client:
        if method.lower() == "get":
            resp = client.get(url, params=data, headers=headers)
        else:
            resp = client.post(url, json=data or {}, headers=headers)

    # 尝试解析 JSON 响应体
    try:
        body = resp.json()
    except Exception as exc:
        raise PlatformApiError(f"平台 API 响应非 JSON：{resp.status_code}") from exc

    if not isinstance(body, dict):
        raise PlatformApiError("平台 API 响应格式异常")

    # 平台统一约定：code === 0 表示成功
    code = body.get("code")
    if code != 0:
        msg = body.get("message") or body.get("data") or "平台 API 调用失败"
        raise PlatformApiError(str(msg), code=code, data=body.get("data"))

    return body.get("data")
