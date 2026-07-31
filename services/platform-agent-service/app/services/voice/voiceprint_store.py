"""声纹库存储：Postgres 优先，未配置时内存回退。"""

from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass
class VoiceprintProfile:
    id: str
    display_name: str
    description: str = ""
    embedding: list[float] = field(default_factory=list)
    sample_count: int = 0
    created_at: str = ""
    updated_at: str = ""

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "display_name": self.display_name,
            "description": self.description,
            "sample_count": self.sample_count,
            "enrolled": self.sample_count > 0 and bool(self.embedding),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class InMemoryVoiceprintStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._items: dict[str, VoiceprintProfile] = {}

    def list_profiles(self) -> list[VoiceprintProfile]:
        with self._lock:
            return sorted(self._items.values(), key=lambda p: p.updated_at, reverse=True)

    def get(self, profile_id: str) -> VoiceprintProfile | None:
        with self._lock:
            return self._items.get(profile_id)

    def create(self, *, display_name: str, description: str = "") -> VoiceprintProfile:
        now = _utcnow().isoformat()
        profile = VoiceprintProfile(
            id=uuid.uuid4().hex,
            display_name=display_name.strip() or "未命名",
            description=(description or "").strip(),
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self._items[profile.id] = profile
        return profile

    def update(
        self,
        profile_id: str,
        *,
        display_name: str | None = None,
        description: str | None = None,
    ) -> VoiceprintProfile | None:
        with self._lock:
            profile = self._items.get(profile_id)
            if profile is None:
                return None
            if display_name is not None:
                profile.display_name = display_name.strip() or profile.display_name
            if description is not None:
                profile.description = description.strip()
            profile.updated_at = _utcnow().isoformat()
            return profile

    def delete(self, profile_id: str) -> bool:
        with self._lock:
            return self._items.pop(profile_id, None) is not None

    def save_embedding(
        self,
        profile_id: str,
        *,
        embedding: list[float],
        sample_count: int,
    ) -> VoiceprintProfile | None:
        with self._lock:
            profile = self._items.get(profile_id)
            if profile is None:
                return None
            profile.embedding = list(embedding)
            profile.sample_count = int(sample_count)
            profile.updated_at = _utcnow().isoformat()
            return profile


class PostgresVoiceprintStore:
    def __init__(self, pool: Any) -> None:
        self._pool = pool

    def list_profiles(self) -> list[VoiceprintProfile]:
        with self._pool.connection() as conn:
            rows = conn.execute(
                """
                SELECT id, display_name, description, embedding, sample_count,
                       created_at, updated_at
                FROM agent_voiceprints
                ORDER BY updated_at DESC
                """
            ).fetchall()
        return [self._row_to_profile(r) for r in rows]

    def get(self, profile_id: str) -> VoiceprintProfile | None:
        with self._pool.connection() as conn:
            row = conn.execute(
                """
                SELECT id, display_name, description, embedding, sample_count,
                       created_at, updated_at
                FROM agent_voiceprints WHERE id = %s
                """,
                (profile_id,),
            ).fetchone()
        return self._row_to_profile(row) if row else None

    def create(self, *, display_name: str, description: str = "") -> VoiceprintProfile:
        profile_id = uuid.uuid4().hex
        name = display_name.strip() or "未命名"
        desc = (description or "").strip()
        with self._pool.connection() as conn:
            row = conn.execute(
                """
                INSERT INTO agent_voiceprints (id, display_name, description, embedding, sample_count)
                VALUES (%s, %s, %s, '[]'::jsonb, 0)
                RETURNING id, display_name, description, embedding, sample_count, created_at, updated_at
                """,
                (profile_id, name, desc),
            ).fetchone()
        return self._row_to_profile(row)

    def update(
        self,
        profile_id: str,
        *,
        display_name: str | None = None,
        description: str | None = None,
    ) -> VoiceprintProfile | None:
        profile = self.get(profile_id)
        if profile is None:
            return None
        name = display_name.strip() if display_name is not None else profile.display_name
        desc = description.strip() if description is not None else profile.description
        if display_name is not None and not name:
            name = profile.display_name
        with self._pool.connection() as conn:
            row = conn.execute(
                """
                UPDATE agent_voiceprints
                SET display_name = %s, description = %s, updated_at = NOW()
                WHERE id = %s
                RETURNING id, display_name, description, embedding, sample_count, created_at, updated_at
                """,
                (name, desc, profile_id),
            ).fetchone()
        return self._row_to_profile(row) if row else None

    def delete(self, profile_id: str) -> bool:
        with self._pool.connection() as conn:
            cur = conn.execute("DELETE FROM agent_voiceprints WHERE id = %s", (profile_id,))
            return (cur.rowcount or 0) > 0

    def save_embedding(
        self,
        profile_id: str,
        *,
        embedding: list[float],
        sample_count: int,
    ) -> VoiceprintProfile | None:
        import json

        with self._pool.connection() as conn:
            row = conn.execute(
                """
                UPDATE agent_voiceprints
                SET embedding = %s::jsonb, sample_count = %s, updated_at = NOW()
                WHERE id = %s
                RETURNING id, display_name, description, embedding, sample_count, created_at, updated_at
                """,
                (json.dumps(embedding), int(sample_count), profile_id),
            ).fetchone()
        return self._row_to_profile(row) if row else None

    @staticmethod
    def _row_to_profile(row: Any) -> VoiceprintProfile:
        emb = row.get("embedding") or []
        if isinstance(emb, str):
            import json

            emb = json.loads(emb)
        created = row.get("created_at")
        updated = row.get("updated_at")
        return VoiceprintProfile(
            id=str(row["id"]),
            display_name=str(row["display_name"]),
            description=str(row.get("description") or ""),
            embedding=[float(x) for x in emb],
            sample_count=int(row.get("sample_count") or 0),
            created_at=created.isoformat() if hasattr(created, "isoformat") else str(created or ""),
            updated_at=updated.isoformat() if hasattr(updated, "isoformat") else str(updated or ""),
        )


_store: InMemoryVoiceprintStore | PostgresVoiceprintStore | None = None
_memory_fallback = InMemoryVoiceprintStore()


def configure_voiceprint_store(
    store: InMemoryVoiceprintStore | PostgresVoiceprintStore | None,
) -> None:
    global _store
    _store = store


def get_voiceprint_store() -> InMemoryVoiceprintStore | PostgresVoiceprintStore:
    if _store is not None:
        return _store
    from app.persistence.bootstrap import get_sync_pool, is_postgres_enabled

    if is_postgres_enabled():
        try:
            pool = get_sync_pool()
            return PostgresVoiceprintStore(pool)
        except Exception:  # noqa: BLE001
            logger.warning("声纹库 Postgres 不可用，回退内存", exc_info=True)
    return _memory_fallback
