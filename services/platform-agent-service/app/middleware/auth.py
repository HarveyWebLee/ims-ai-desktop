"""
JWT 校验与用户上下文注入模块（Phase 0 简化实现）

文件职责
--------
从 HTTP ``Authorization`` 头得到「当前是谁」：
- 会话隔离用的 ``user_id``（hash，非明文）
- 平台写操作用的 ``username``（从 JWT payload 声明读取，不验签）

白话概念
--------
前端登录后每次请求带 Bearer Token。Agent 服务用它做两件事：
1) 把同一 token 稳定映射成 user_id，避免 A 看到 B 的会话列表；
2) 调平台确认告警等 API 时补全 confirmPerson 等字段。

在 Agent 流程中的位置
--------------------
  FastAPI 路由 / 依赖注入
    → get_current_user_id / require_auth
  Server Tools（如 batch_confirm）
    → get_username_from_token(current_auth_token)

当前阶段策略（务必知晓）
------------------------
- 有 token → SHA256 前 8 位 → ``user_<hex>``
- 无 token → ``anonymous``
- **不做完整 JWT 验签**；生产应校验签名、过期与 issuer

如何被调用
----------
  @router.get("/xxx")
  async def handler(user_id: str = Depends(get_current_user_id)):
      ...
  或在 handler 内显式 ``await get_current_user_id(authorization)``。
"""

from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

# Header：从请求头读取参数；HTTPException：返回 401 等 HTTP 错误
from fastapi import Header, HTTPException


def resolve_user_id_from_token(authorization: str | None) -> str:
    """
    同步解析 Authorization 对应的稳定 user_id。

    供工具授权等非 FastAPI 路径使用；语义与 get_current_user_id 一致。
    """
    if not authorization:
        return "anonymous"
    token = authorization.replace("Bearer ", "").strip()
    if not token:
        return "anonymous"
    # 使用 SHA256 前 8 位，避免内置 hash() 随进程 PYTHONHASHSEED 变化导致重启后会话归属失效
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()[:8]
    return f"user_{digest}"


async def get_current_user_id(
    authorization: str | None = Header(default=None),
) -> str:
    """
    从 Authorization 请求头提取用户标识（FastAPI 依赖项）。

    参数：
        authorization: 可选，通常为 "Bearer <JWT>" 格式

    返回：
        - 无 token 或空 token → "anonymous"
        - 有 token → "user_<8位十六进制hash>"，同一 token 始终映射到同一 user_id

    说明：
        Phase 0 简化实现，生产环境应：
        1. 校验 JWT 签名与过期时间
        2. 从 payload 的 sub 等字段读取真实用户 ID
    """
    return resolve_user_id_from_token(authorization)


def decode_jwt_payload(token: str) -> dict[str, Any]:
    """
    解析 JWT 中间段 payload（Base64URL → JSON，**不验签**）。

    参数
    ----
    token : str
        原始 JWT 或带 Bearer 前缀的字符串。

    返回
    ----
    dict
        声明字典；格式非法时返回空 dict。

    用途
    ----
    Server Tool 读取 username 等，供 confirmAlarm 补全 confirmPerson。
    """
    raw = (token or "").replace("Bearer ", "").strip()
    parts = raw.split(".")
    if len(parts) != 3:
        return {}
    segment = parts[1]
    pad = (-len(segment)) % 4
    if pad:
        segment += "=" * pad
    try:
        decoded = base64.urlsafe_b64decode(segment.encode("ascii"))
        data: Any = json.loads(decoded.decode("utf-8"))
        return data if isinstance(data, dict) else {}
    except ValueError, json.JSONDecodeError, UnicodeDecodeError:
        return {}


def get_username_from_token(authorization: str | None) -> str | None:
    """
    从 Authorization 头提取平台用户名（confirmPerson 等场景）。

    依次尝试常见 claim：username、userName、sub。
    """
    token = (authorization or "").replace("Bearer ", "").strip()
    if not token:
        return None
    payload = decode_jwt_payload(token)
    for key in ("username", "userName", "sub", "name"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _normalize_permission_list(value: object) -> list[str]:
    """将 JWT claim 中的权限声明规范化为字符串列表。"""
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        if "," in text:
            return [part.strip() for part in text.split(",") if part.strip()]
        return [text]
    if isinstance(value, (list, tuple, set, frozenset)):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def resolve_permissions_from_token(authorization: str | None) -> list[str] | None:
    """
    从 JWT claims 解析权限列表（有来源才返回，无声明则返回 None）。

    兼容常见键：permissions / scopes / authorities / perms。
    未解析到任何权限时返回 None，表示「上下文未注入权限」——
    CatalogRequiredPermissionsPolicy 在 fail_closed 下将拒绝含 required_permissions 的写工具。
    """
    token = (authorization or "").replace("Bearer ", "").strip()
    if not token:
        return None
    payload = decode_jwt_payload(token)
    for key in ("permissions", "scopes", "authorities", "perms"):
        perms = _normalize_permission_list(payload.get(key))
        if perms:
            return perms
    return None


async def require_auth(
    authorization: str | None = Header(default=None),
) -> str:
    """
    要求已登录的接口依赖项：匿名用户直接 401。

    返回：
        非 anonymous 的 user_id 字符串

    异常：
        HTTPException 401 — 未携带有效 Authorization
    """
    user_id = await get_current_user_id(authorization)
    if user_id == "anonymous":
        raise HTTPException(status_code=401, detail="未授权")
    return user_id
