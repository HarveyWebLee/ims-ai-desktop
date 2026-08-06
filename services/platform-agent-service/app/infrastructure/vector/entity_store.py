"""
Qdrant 实体集合写入：稳定 Point ID（不含正文），供设备/变量等同步使用。
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from typing import Any

from app.config import settings
from app.infrastructure.vector.client import get_qdrant_client
from app.infrastructure.vector.embeddings import resolve_embeddings

logger = logging.getLogger(__name__)


def _entity_point_id(collection: str, entity_type: str, entity_key: str) -> str:
    digest = hashlib.sha256(f"{collection}|{entity_type}|{entity_key}".encode()).hexdigest()
    return str(uuid.UUID(digest[:32]))


class EntityVectorStore:
    """面向结构化实体的 Qdrant 封装。"""

    def __init__(
        self,
        *,
        collection: str | None = None,
        client: Any | None = None,
        embeddings: Any | None = None,
    ) -> None:
        self.collection = collection or settings.qdrant_collection_entities
        self._client = client
        self._embeddings = embeddings

    @property
    def client(self):
        if self._client is None:
            self._client = get_qdrant_client()
        return self._client

    @property
    def embeddings(self):
        if self._embeddings is None:
            self._embeddings = resolve_embeddings()
        return self._embeddings

    def ensure_collection(self) -> None:
        from qdrant_client.models import Distance, VectorParams

        if self.client.collection_exists(self.collection):
            return
        self.client.create_collection(
            collection_name=self.collection,
            vectors_config=VectorParams(
                size=settings.qdrant_vector_size,
                distance=Distance.COSINE,
            ),
        )
        logger.info("已创建实体 collection=%s", self.collection)

    def upsert_entities(
        self,
        items: list[dict[str, Any]],
    ) -> int:
        """
        批量 upsert 实体。

        每项需含：entity_type, entity_key, text；可选 source / payload。
        """
        from qdrant_client.models import PointStruct

        if not items:
            return 0
        self.ensure_collection()
        batch_size = max(1, int(settings.vector_upsert_batch_size))
        total = 0
        for start in range(0, len(items), batch_size):
            batch = items[start : start + batch_size]
            texts = [str(it.get("text") or "") for it in batch]
            vectors = self.embeddings.embed_documents(texts)
            points: list[PointStruct] = []
            for item, vector, text in zip(batch, vectors, texts, strict=True):
                entity_type = str(item.get("entity_type") or "table_row")
                entity_key = str(item.get("entity_key") or "")
                source = str(item.get("source") or f"dm:{entity_type}:{entity_key}")
                point_id = _entity_point_id(self.collection, entity_type, entity_key)
                payload = {
                    **(item.get("payload") or {}),
                    "source": source,
                    "text": text,
                    "entity_type": entity_type,
                    "entity_key": entity_key,
                    "media_kind": "entity",
                }
                points.append(PointStruct(id=point_id, vector=vector, payload=payload))
            self.client.upsert(collection_name=self.collection, points=points, wait=True)
            total += len(points)
        return total

    def similarity_search(
        self,
        query: str,
        *,
        limit: int = 5,
        score_threshold: float | None = None,
        entity_types: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        语义检索实体；集合不存在或查询为空时返回 []。

        返回项含：text, score, payload, entity_type, entity_key。
        """
        q = (query or "").strip()
        if not q:
            return []
        if not self.client.collection_exists(self.collection):
            return []

        # 多取若干再按 entity_type 本地过滤，避免依赖尚未建的 payload 索引
        type_set = {t for t in (entity_types or []) if t}
        fetch_limit = max(1, limit * 3 if type_set else limit)
        vector = self.embeddings.embed_query(q)
        result = self.client.query_points(
            collection_name=self.collection,
            query=vector,
            limit=fetch_limit,
            score_threshold=score_threshold,
            with_payload=True,
        )
        hits: list[dict[str, Any]] = []
        for point in result.points:
            payload = dict(point.payload or {})
            entity_type = str(payload.get("entity_type") or "")
            if type_set and entity_type not in type_set:
                continue
            hits.append(
                {
                    "text": str(payload.get("text") or ""),
                    "score": float(point.score or 0.0),
                    "payload": payload,
                    "entity_type": entity_type,
                    "entity_key": str(payload.get("entity_key") or ""),
                    "source": str(payload.get("source") or ""),
                }
            )
            if len(hits) >= limit:
                break
        return hits

    def count(self) -> int:
        """当前实体 collection 点数；集合不存在时返回 0。"""
        if not self.client.collection_exists(self.collection):
            return 0
        info = self.client.get_collection(self.collection)
        return int(info.points_count or 0)

    def drop_collection(self) -> bool:
        """删除整个实体 collection；不存在返回 False。"""
        if not self.client.collection_exists(self.collection):
            return False
        self.client.delete_collection(self.collection)
        logger.warning("已删除实体 Qdrant collection=%s", self.collection)
        return True
