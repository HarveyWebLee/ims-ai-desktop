"""
Qdrant 客户端工厂与连通性探测。

文件职责
--------
按 ``settings.qdrant_url`` 创建 ``QdrantClient`` 单例，供入库脚本与检索服务复用。
未配置 URL 时视为禁用向量能力。
"""

from __future__ import annotations

import logging
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

_client: Any | None = None


def is_qdrant_configured() -> bool:
    """是否配置了非空的 Qdrant URL。"""
    return bool(settings.qdrant_url and settings.qdrant_url.strip())


def get_qdrant_client(*, force_new: bool = False):
    """
    获取进程内 QdrantClient 单例。

    参数：
        force_new: True 时关闭旧连接并新建（测试 / 热更新配置时用）

    异常：
        RuntimeError — 未配置 ``QDRANT_URL``
    """
    global _client
    if not is_qdrant_configured():
        raise RuntimeError("未配置 QDRANT_URL，无法连接 Qdrant")

    if _client is not None and not force_new:
        return _client

    from qdrant_client import QdrantClient

    if _client is not None:
        try:
            _client.close()
        except Exception:  # noqa: BLE001 — 关闭旧连接失败不阻断新建
            logger.debug("关闭旧 QdrantClient 失败", exc_info=True)

    kwargs: dict[str, Any] = {"url": settings.qdrant_url.strip()}
    if settings.qdrant_api_key:
        kwargs["api_key"] = settings.qdrant_api_key

    _client = QdrantClient(**kwargs)
    return _client


def close_qdrant_client() -> None:
    """关闭并清空全局客户端（应用 shutdown 时调用）。"""
    global _client
    if _client is None:
        return
    try:
        _client.close()
    except Exception:  # noqa: BLE001
        logger.debug("关闭 QdrantClient 失败", exc_info=True)
    _client = None


def probe_qdrant() -> dict[str, Any]:
    """
    探测 Qdrant 连通性，供 ``GET /health`` 与运维脚本使用。

    返回字段：
        enabled: 是否配置了 URL
        ok: 是否可列出 collection
        url: 配置的 URL（可能为空）
        collections: collection 名称列表（失败时为空）
        error: 失败原因（成功时为空字符串）
    """
    if not is_qdrant_configured():
        return {
            "enabled": False,
            "ok": False,
            "url": "",
            "collections": [],
            "error": "QDRANT_URL 未配置",
        }

    url = settings.qdrant_url.strip()
    try:
        client = get_qdrant_client()
        resp = client.get_collections()
        names = [c.name for c in resp.collections]
        return {
            "enabled": True,
            "ok": True,
            "url": url,
            "collections": names,
            "error": "",
        }
    except Exception as exc:  # noqa: BLE001 — 健康检查需吞异常并回报
        logger.warning("Qdrant 连通性探测失败: %s", exc)
        return {
            "enabled": True,
            "ok": False,
            "url": url,
            "collections": [],
            "error": str(exc),
        }
