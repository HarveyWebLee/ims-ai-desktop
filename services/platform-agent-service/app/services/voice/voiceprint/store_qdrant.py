"""声纹向量：Qdrant 主存储 + 内存回退（单测 / 无 Qdrant）。"""

from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass
from typing import Any

from app.config import settings
from app.services.voice.voiceprint.embedding import cosine_similarity, embedding_dim

logger = logging.getLogger(__name__)


@dataclass
class VectorHit:
    sample_id: str
    profile_id: str
    display_name: str
    score: float
    embedding: list[float]


class InMemoryVectorIndex:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._points: dict[str, dict[str, Any]] = {}

    def ensure_ready(self) -> None:
        return

    def upsert(
        self,
        *,
        sample_id: str,
        embedding: list[float],
        profile_id: str,
        display_name: str,
        model_id: str,
        device_hint: str = "",
        env_hint: str = "",
    ) -> None:
        with self._lock:
            self._points[sample_id] = {
                "embedding": list(embedding),
                "profile_id": profile_id,
                "display_name": display_name,
                "model_id": model_id,
                "device_hint": device_hint,
                "env_hint": env_hint,
            }

    def delete_sample(self, sample_id: str) -> None:
        with self._lock:
            self._points.pop(sample_id, None)

    def delete_profile(self, profile_id: str) -> None:
        with self._lock:
            dead = [k for k, v in self._points.items() if v.get("profile_id") == profile_id]
            for key in dead:
                self._points.pop(key, None)

    def list_by_profile(self, profile_id: str) -> list[tuple[str, list[float]]]:
        with self._lock:
            return [
                (sid, list(v["embedding"]))
                for sid, v in self._points.items()
                if v.get("profile_id") == profile_id
            ]

    def search(self, embedding: list[float], *, top_k: int) -> list[VectorHit]:
        with self._lock:
            scored: list[VectorHit] = []
            for sid, meta in self._points.items():
                score = cosine_similarity(embedding, meta["embedding"])
                scored.append(
                    VectorHit(
                        sample_id=sid,
                        profile_id=str(meta["profile_id"]),
                        display_name=str(meta.get("display_name") or ""),
                        score=score,
                        embedding=list(meta["embedding"]),
                    )
                )
            scored.sort(key=lambda h: h.score, reverse=True)
            return scored[: max(1, top_k)]

    def collection_exists(self) -> bool:
        return True


class QdrantVectorIndex:
    def __init__(self) -> None:
        self._ensured = False

    @property
    def collection(self) -> str:
        return (settings.voiceprint_qdrant_collection or "agent_voiceprints").strip()

    def _client(self):
        from app.infrastructure.vector.client import get_qdrant_client

        return get_qdrant_client()

    def ensure_ready(self) -> None:
        if self._ensured:
            return
        from qdrant_client.models import Distance, VectorParams

        client = self._client()
        name = self.collection
        dim = embedding_dim()
        if client.collection_exists(name):
            info = client.get_collection(name)
            # 维度不匹配则重建（破坏性，符合方案）
            existing = getattr(getattr(info, "config", None), "params", None)
            vectors = getattr(existing, "vectors", None)
            size = getattr(vectors, "size", None)
            if size is not None and int(size) != dim:
                logger.warning(
                    "声纹 collection 维度不匹配 size=%s expect=%s，重建 %s",
                    size,
                    dim,
                    name,
                )
                client.delete_collection(name)
            else:
                self._ensured = True
                return
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )
        logger.info("已创建声纹 Qdrant collection=%s dim=%s", name, dim)
        self._ensured = True

    @staticmethod
    def _point_uuid(sample_id: str) -> str:
        try:
            return str(uuid.UUID(sample_id))
        except ValueError:
            return str(uuid.UUID(hex=sample_id[:32].ljust(32, "0")))

    def upsert(
        self,
        *,
        sample_id: str,
        embedding: list[float],
        profile_id: str,
        display_name: str,
        model_id: str,
        device_hint: str = "",
        env_hint: str = "",
    ) -> None:
        from qdrant_client.models import PointStruct

        self.ensure_ready()
        self._client().upsert(
            collection_name=self.collection,
            points=[
                PointStruct(
                    id=self._point_uuid(sample_id),
                    vector=list(embedding),
                    payload={
                        "sample_id": sample_id,
                        "profile_id": profile_id,
                        "display_name": display_name,
                        "model_id": model_id,
                        "device_hint": device_hint,
                        "env_hint": env_hint,
                    },
                )
            ],
            wait=True,
        )

    def delete_sample(self, sample_id: str) -> None:
        from qdrant_client.models import PointIdsList

        self.ensure_ready()
        self._client().delete(
            collection_name=self.collection,
            points_selector=PointIdsList(points=[self._point_uuid(sample_id)]),
            wait=True,
        )

    def delete_profile(self, profile_id: str) -> None:
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        self.ensure_ready()
        self._client().delete(
            collection_name=self.collection,
            points_selector=Filter(
                must=[FieldCondition(key="profile_id", match=MatchValue(value=profile_id))]
            ),
            wait=True,
        )

    def list_by_profile(self, profile_id: str) -> list[tuple[str, list[float]]]:
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        self.ensure_ready()
        client = self._client()
        out: list[tuple[str, list[float]]] = []
        offset = None
        while True:
            records, offset = client.scroll(
                collection_name=self.collection,
                scroll_filter=Filter(
                    must=[FieldCondition(key="profile_id", match=MatchValue(value=profile_id))]
                ),
                limit=64,
                offset=offset,
                with_vectors=True,
                with_payload=True,
            )
            for rec in records:
                payload = rec.payload or {}
                sid = str(payload.get("sample_id") or rec.id)
                vec = rec.vector
                if isinstance(vec, dict):
                    vec = next(iter(vec.values()), [])
                out.append((sid, [float(x) for x in (vec or [])]))
            if offset is None:
                break
        return out

    def search(self, embedding: list[float], *, top_k: int) -> list[VectorHit]:
        self.ensure_ready()
        result = self._client().query_points(
            collection_name=self.collection,
            query=list(embedding),
            limit=max(1, top_k),
            with_payload=True,
        )
        out: list[VectorHit] = []
        for hit in result.points:
            payload = hit.payload or {}
            out.append(
                VectorHit(
                    sample_id=str(payload.get("sample_id") or hit.id),
                    profile_id=str(payload.get("profile_id") or ""),
                    display_name=str(payload.get("display_name") or ""),
                    score=float(hit.score or 0.0),
                    embedding=[],
                )
            )
        return out

    def collection_exists(self) -> bool:
        try:
            from app.infrastructure.vector.client import is_qdrant_configured

            if not is_qdrant_configured():
                return False
            return bool(self._client().collection_exists(self.collection))
        except Exception:  # noqa: BLE001
            return False


_index: InMemoryVectorIndex | QdrantVectorIndex | None = None
_memory_index = InMemoryVectorIndex()


def configure_vector_index(index: InMemoryVectorIndex | QdrantVectorIndex | None) -> None:
    global _index
    _index = index


def get_vector_index() -> InMemoryVectorIndex | QdrantVectorIndex:
    if _index is not None:
        return _index
    from app.infrastructure.vector.client import is_qdrant_configured

    if is_qdrant_configured():
        try:
            return QdrantVectorIndex()
        except Exception:  # noqa: BLE001
            logger.warning("声纹 Qdrant 不可用，回退内存向量索引", exc_info=True)
    return _memory_index
