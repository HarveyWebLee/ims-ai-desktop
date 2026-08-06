"""
Playbook 语义检索：短索引向量化 → Qdrant，按用户话术召回 id。

失败/未配置时返回空（不阻断关键词匹配主路径）。
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from typing import Any

from app.config import settings
from app.services.playbook.loader import Playbook

logger = logging.getLogger(__name__)

# 索引正文上限：短索引 + 正文摘要，避免堆成第二 prompt
_INDEX_BODY_CHARS = 1200


def _point_id(collection: str, playbook_id: str) -> str:
    digest = hashlib.sha256(f"{collection}|playbook|{playbook_id}".encode()).hexdigest()
    return str(uuid.UUID(digest[:32]))


def playbook_index_text(playbook: Playbook) -> str:
    """供 Embedding 的短索引文本（标题 + 触发词 + 正文截断）。"""
    triggers = "、".join(playbook.triggers)
    domains = "、".join(playbook.domains)
    body = (playbook.body or "").strip()
    if len(body) > _INDEX_BODY_CHARS:
        body = body[:_INDEX_BODY_CHARS] + "…"
    parts = [
        f"标题：{playbook.title}",
        f"id：{playbook.id}",
        f"触发词：{triggers}" if triggers else "",
        f"领域：{domains}" if domains else "",
        body,
    ]
    return "\n".join(p for p in parts if p).strip()


def reindex_playbooks(playbooks: list[Playbook]) -> int:
    """
    将当前 playbook 列表 upsert 到专用 collection。

    返回写入条数；跳过/失败返回 0。
    """
    if not settings.agent_playbook_semantic_enabled:
        return 0
    if not (settings.qdrant_url or "").strip():
        return 0
    if not playbooks:
        return 0

    try:
        from qdrant_client.models import Distance, PointStruct, VectorParams

        from app.infrastructure.vector.client import get_qdrant_client, is_qdrant_configured
        from app.infrastructure.vector.embeddings import resolve_embeddings

        if not is_qdrant_configured():
            return 0

        collection = settings.qdrant_collection_playbooks
        client = get_qdrant_client()
        if not client.collection_exists(collection):
            client.create_collection(
                collection_name=collection,
                vectors_config=VectorParams(
                    size=settings.qdrant_vector_size,
                    distance=Distance.COSINE,
                ),
            )
            logger.info("已创建 playbook collection=%s", collection)

        embeddings = resolve_embeddings()
        texts = [playbook_index_text(pb) for pb in playbooks]
        vectors = embeddings.embed_documents(texts)
        points: list[Any] = []
        for pb, vector, text in zip(playbooks, vectors, texts, strict=True):
            points.append(
                PointStruct(
                    id=_point_id(collection, pb.id),
                    vector=vector,
                    payload={
                        "playbook_id": pb.id,
                        "title": pb.title,
                        "domains": list(pb.domains),
                        "priority": pb.priority,
                        "text": text,
                        "kind": "playbook",
                    },
                )
            )
        client.upsert(collection_name=collection, points=points)
        logger.info("playbook semantic reindex ok: count=%s", len(points))
        return len(points)
    except Exception:  # noqa: BLE001
        logger.exception("playbook semantic reindex failed")
        return 0


def semantic_search_playbook_ids(
    query: str,
    *,
    limit: int | None = None,
) -> list[tuple[str, float]]:
    """
    语义召回 (playbook_id, score)。

    score 为 Qdrant 相似度（越高越相关）；失败返回 []。
    """
    q = (query or "").strip()
    if not q or not settings.agent_playbook_semantic_enabled:
        return []
    if not (settings.qdrant_url or "").strip():
        return []

    top_k = limit if limit is not None else max(1, int(settings.agent_playbook_max_matches) + 1)
    threshold = float(settings.agent_playbook_semantic_score_threshold)

    try:
        from app.infrastructure.vector.client import get_qdrant_client, is_qdrant_configured
        from app.infrastructure.vector.embeddings import resolve_embeddings

        if not is_qdrant_configured():
            return []
        collection = settings.qdrant_collection_playbooks
        client = get_qdrant_client()
        if not client.collection_exists(collection):
            return []

        vector = resolve_embeddings().embed_query(q)
        result = client.query_points(
            collection_name=collection,
            query=vector,
            limit=max(1, top_k),
            score_threshold=threshold if threshold > 0 else None,
            with_payload=True,
        )
        out: list[tuple[str, float]] = []
        for hit in result.points or []:
            payload = dict(hit.payload or {})
            pid = str(payload.get("playbook_id") or "").strip()
            if not pid:
                continue
            out.append((pid, float(hit.score or 0.0)))
        return out
    except Exception:  # noqa: BLE001
        logger.exception("playbook semantic search failed")
        return []
