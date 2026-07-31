"""Stage 2：Correction Cache（Redis 纠错映射，毫秒级）。"""

from __future__ import annotations

import hashlib
import logging
import re

from app.config import settings

logger = logging.getLogger(__name__)

_KEY_PREFIX = "asr:corr:v1:"
_NORMALIZE_SPACE_RE = re.compile(r"\s+")


def normalize_cache_key(text: str) -> str:
    """缓存键规范化：去首尾空白、合并空白、小写（便于英文别名命中）。"""
    t = _NORMALIZE_SPACE_RE.sub(" ", (text or "").strip())
    return t.casefold()


def _redis_key(normalized: str) -> str:
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:40]
    return f"{_KEY_PREFIX}{digest}"


def cache_get(raw_text: str) -> str | None:
    """查询纠错映射；未配置/失败返回 None。"""
    key_text = normalize_cache_key(raw_text)
    if not key_text:
        return None
    try:
        from app.infrastructure.redis.client import get_redis_client, is_redis_configured

        if not is_redis_configured():
            return None
        client = get_redis_client()
        value = client.get(_redis_key(key_text))
        if isinstance(value, str) and value:
            return value
        return None
    except Exception as exc:  # noqa: BLE001
        logger.debug("correction cache get failed: %s", exc)
        return None


def cache_set(raw_text: str, corrected: str) -> None:
    """写入纠错映射（Dictionary / Vector / LLM 成功后）。"""
    key_text = normalize_cache_key(raw_text)
    value = (corrected or "").strip()
    if not key_text or not value:
        return
    # 与规范化键完全相同则无需缓存
    if normalize_cache_key(value) == key_text and value == (raw_text or "").strip():
        return
    try:
        from app.infrastructure.redis.client import get_redis_client, is_redis_configured

        if not is_redis_configured():
            return
        ttl = max(60, int(settings.transcribe_correct_cache_ttl_seconds))
        client = get_redis_client()
        client.set(_redis_key(key_text), value, ex=ttl)
    except Exception as exc:  # noqa: BLE001
        logger.debug("correction cache set failed: %s", exc)
