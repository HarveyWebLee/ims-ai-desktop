"""
Redis 连接与健康探测。

宿主机默认 ``redis://127.0.0.1:13386/0``（docker-compose 映射 13386→6379）。
未配置或不可达时业务侧应 fail-open，不阻断主流程。
"""

from __future__ import annotations

import logging
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

_client: Any | None = None


def is_redis_configured() -> bool:
    return bool((settings.redis_url or "").strip())


def get_redis_client():
    """
    懒加载同步 Redis 客户端（redis-py）。

    返回:
        redis.Redis 实例

    异常:
        ValueError: 未配置 REDIS_URL
        ImportError: 未安装 redis 包
    """
    global _client
    if _client is not None:
        return _client
    url = (settings.redis_url or "").strip()
    if not url:
        raise ValueError("未配置 REDIS_URL")
    import redis

    _client = redis.Redis.from_url(
        url,
        decode_responses=True,
        socket_connect_timeout=2.0,
        socket_timeout=2.0,
    )
    return _client


def close_redis_client() -> None:
    global _client
    if _client is None:
        return
    try:
        _client.close()
    except Exception:  # noqa: BLE001
        logger.debug("close redis failed", exc_info=True)
    _client = None


def probe_redis() -> dict[str, Any]:
    """供 /health 使用：enabled / ok / error。"""
    if not is_redis_configured():
        return {"enabled": False, "ok": False, "error": "REDIS_URL empty"}
    try:
        client = get_redis_client()
        pong = client.ping()
        return {
            "enabled": True,
            "ok": bool(pong),
            "url": settings.redis_url,
        }
    except Exception as exc:  # noqa: BLE001
        logger.debug("redis probe failed: %s", exc)
        return {
            "enabled": True,
            "ok": False,
            "url": settings.redis_url,
            "error": str(exc),
        }
