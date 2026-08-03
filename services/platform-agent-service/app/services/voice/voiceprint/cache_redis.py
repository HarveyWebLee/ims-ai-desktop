"""声纹 Redis 热缓存。"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def _emb_key(profile_id: str) -> str:
    return f"vp:emb:{profile_id}"


def _meta_key(profile_id: str) -> str:
    return f"vp:meta:{profile_id}"


def invalidate_profile(profile_id: str) -> None:
    try:
        from app.infrastructure.redis.client import get_redis_client, is_redis_configured

        if not is_redis_configured():
            return
        client = get_redis_client()
        client.delete(_emb_key(profile_id), _meta_key(profile_id))
    except Exception:  # noqa: BLE001
        logger.debug("声纹缓存 invalidate 失败 profile=%s", profile_id, exc_info=True)


def cache_embeddings(profile_id: str, embeddings: list[list[float]], meta: dict[str, Any]) -> None:
    try:
        from app.config import settings
        from app.infrastructure.redis.client import get_redis_client, is_redis_configured

        if not is_redis_configured():
            return
        ttl = max(60, int(settings.voiceprint_redis_ttl_sec or 3600))
        client = get_redis_client()
        client.set(_emb_key(profile_id), json.dumps(embeddings), ex=ttl)
        client.set(_meta_key(profile_id), json.dumps(meta), ex=ttl)
    except Exception:  # noqa: BLE001
        logger.debug("声纹缓存写入失败 profile=%s", profile_id, exc_info=True)


def get_cached_embeddings(profile_id: str) -> list[list[float]] | None:
    try:
        from app.infrastructure.redis.client import get_redis_client, is_redis_configured

        if not is_redis_configured():
            return None
        raw = get_redis_client().get(_emb_key(profile_id))
        if not raw:
            return None
        data = json.loads(raw)
        if not isinstance(data, list):
            return None
        return [[float(x) for x in row] for row in data]
    except Exception:  # noqa: BLE001
        logger.debug("声纹缓存读取失败 profile=%s", profile_id, exc_info=True)
        return None
