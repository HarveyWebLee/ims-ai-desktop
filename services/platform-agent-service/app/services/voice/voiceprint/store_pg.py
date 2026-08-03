"""声纹 Postgres / 内存元数据存储。"""

from __future__ import annotations

import logging
import threading
import uuid
from datetime import UTC, datetime
from typing import Any, Protocol

from app.services.voice.voiceprint.types import ProfileStatus, VoiceprintProfile, VoiceprintSample

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _iso(value: Any) -> str:
    if hasattr(value, "isoformat"):
        return str(value.isoformat())
    return str(value or "")


class ProfileStore(Protocol):
    def list_profiles(self) -> list[VoiceprintProfile]: ...
    def get(self, profile_id: str) -> VoiceprintProfile | None: ...
    def create(self, *, display_name: str, description: str = "") -> VoiceprintProfile: ...
    def update(
        self,
        profile_id: str,
        *,
        display_name: str | None = None,
        description: str | None = None,
        status: ProfileStatus | None = None,
    ) -> VoiceprintProfile | None: ...
    def delete(self, profile_id: str) -> bool: ...
    def list_samples(self, profile_id: str) -> list[VoiceprintSample]: ...
    def add_sample(
        self,
        profile_id: str,
        *,
        sample_id: str,
        model_id: str,
        duration_ms: int,
        device_hint: str = "",
        env_hint: str = "",
    ) -> VoiceprintSample | None: ...
    def delete_sample(self, profile_id: str, sample_id: str) -> bool: ...
    def set_counts(
        self,
        profile_id: str,
        *,
        sample_count: int,
        model_id: str,
        status: ProfileStatus,
    ) -> VoiceprintProfile | None: ...


class InMemoryProfileStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._profiles: dict[str, VoiceprintProfile] = {}
        self._samples: dict[str, list[VoiceprintSample]] = {}

    def list_profiles(self) -> list[VoiceprintProfile]:
        with self._lock:
            return sorted(self._profiles.values(), key=lambda p: p.updated_at, reverse=True)

    def get(self, profile_id: str) -> VoiceprintProfile | None:
        with self._lock:
            return self._profiles.get(profile_id)

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
            self._profiles[profile.id] = profile
            self._samples[profile.id] = []
        return profile

    def update(
        self,
        profile_id: str,
        *,
        display_name: str | None = None,
        description: str | None = None,
        status: ProfileStatus | None = None,
    ) -> VoiceprintProfile | None:
        with self._lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                return None
            if display_name is not None:
                profile.display_name = display_name.strip() or profile.display_name
            if description is not None:
                profile.description = description.strip()
            if status is not None:
                profile.status = status
            profile.updated_at = _utcnow().isoformat()
            return profile

    def delete(self, profile_id: str) -> bool:
        with self._lock:
            self._samples.pop(profile_id, None)
            return self._profiles.pop(profile_id, None) is not None

    def list_samples(self, profile_id: str) -> list[VoiceprintSample]:
        with self._lock:
            return list(self._samples.get(profile_id, []))

    def add_sample(
        self,
        profile_id: str,
        *,
        sample_id: str,
        model_id: str,
        duration_ms: int,
        device_hint: str = "",
        env_hint: str = "",
    ) -> VoiceprintSample | None:
        with self._lock:
            if profile_id not in self._profiles:
                return None
            sample = VoiceprintSample(
                id=sample_id,
                profile_id=profile_id,
                model_id=model_id,
                duration_ms=duration_ms,
                device_hint=device_hint,
                env_hint=env_hint,
                created_at=_utcnow().isoformat(),
            )
            self._samples.setdefault(profile_id, []).append(sample)
            return sample

    def delete_sample(self, profile_id: str, sample_id: str) -> bool:
        with self._lock:
            items = self._samples.get(profile_id)
            if not items:
                return False
            before = len(items)
            self._samples[profile_id] = [s for s in items if s.id != sample_id]
            return len(self._samples[profile_id]) < before

    def set_counts(
        self,
        profile_id: str,
        *,
        sample_count: int,
        model_id: str,
        status: ProfileStatus,
    ) -> VoiceprintProfile | None:
        with self._lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                return None
            profile.sample_count = int(sample_count)
            profile.model_id = model_id
            profile.status = status
            profile.updated_at = _utcnow().isoformat()
            return profile


class PostgresProfileStore:
    def __init__(self, pool: Any) -> None:
        self._pool = pool

    def list_profiles(self) -> list[VoiceprintProfile]:
        with self._pool.connection() as conn:
            rows = conn.execute(
                """
                SELECT id, display_name, description, model_id, sample_count, status,
                       created_at, updated_at
                FROM agent_voiceprint_profiles
                ORDER BY updated_at DESC
                """
            ).fetchall()
        return [self._row_to_profile(r) for r in rows]

    def get(self, profile_id: str) -> VoiceprintProfile | None:
        with self._pool.connection() as conn:
            row = conn.execute(
                """
                SELECT id, display_name, description, model_id, sample_count, status,
                       created_at, updated_at
                FROM agent_voiceprint_profiles WHERE id = %s
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
                INSERT INTO agent_voiceprint_profiles
                    (id, display_name, description, model_id, sample_count, status)
                VALUES (%s, %s, %s, '', 0, 'pending')
                RETURNING id, display_name, description, model_id, sample_count, status,
                          created_at, updated_at
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
        status: ProfileStatus | None = None,
    ) -> VoiceprintProfile | None:
        profile = self.get(profile_id)
        if profile is None:
            return None
        name = display_name.strip() if display_name is not None else profile.display_name
        desc = description.strip() if description is not None else profile.description
        if display_name is not None and not name:
            name = profile.display_name
        next_status = status or profile.status
        with self._pool.connection() as conn:
            row = conn.execute(
                """
                UPDATE agent_voiceprint_profiles
                SET display_name = %s, description = %s, status = %s, updated_at = NOW()
                WHERE id = %s
                RETURNING id, display_name, description, model_id, sample_count, status,
                          created_at, updated_at
                """,
                (name, desc, next_status, profile_id),
            ).fetchone()
        return self._row_to_profile(row) if row else None

    def delete(self, profile_id: str) -> bool:
        with self._pool.connection() as conn:
            cur = conn.execute("DELETE FROM agent_voiceprint_profiles WHERE id = %s", (profile_id,))
            return (cur.rowcount or 0) > 0

    def list_samples(self, profile_id: str) -> list[VoiceprintSample]:
        with self._pool.connection() as conn:
            rows = conn.execute(
                """
                SELECT id, profile_id, model_id, duration_ms, device_hint, env_hint, created_at
                FROM agent_voiceprint_samples
                WHERE profile_id = %s
                ORDER BY created_at ASC
                """,
                (profile_id,),
            ).fetchall()
        return [self._row_to_sample(r) for r in rows]

    def add_sample(
        self,
        profile_id: str,
        *,
        sample_id: str,
        model_id: str,
        duration_ms: int,
        device_hint: str = "",
        env_hint: str = "",
    ) -> VoiceprintSample | None:
        if self.get(profile_id) is None:
            return None
        with self._pool.connection() as conn:
            row = conn.execute(
                """
                INSERT INTO agent_voiceprint_samples
                    (id, profile_id, model_id, duration_ms, device_hint, env_hint)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, profile_id, model_id, duration_ms, device_hint, env_hint, created_at
                """,
                (
                    sample_id,
                    profile_id,
                    model_id,
                    int(duration_ms),
                    (device_hint or "").strip(),
                    (env_hint or "").strip(),
                ),
            ).fetchone()
        return self._row_to_sample(row)

    def delete_sample(self, profile_id: str, sample_id: str) -> bool:
        with self._pool.connection() as conn:
            cur = conn.execute(
                """
                DELETE FROM agent_voiceprint_samples
                WHERE profile_id = %s AND id = %s
                """,
                (profile_id, sample_id),
            )
            return (cur.rowcount or 0) > 0

    def set_counts(
        self,
        profile_id: str,
        *,
        sample_count: int,
        model_id: str,
        status: ProfileStatus,
    ) -> VoiceprintProfile | None:
        with self._pool.connection() as conn:
            row = conn.execute(
                """
                UPDATE agent_voiceprint_profiles
                SET sample_count = %s, model_id = %s, status = %s, updated_at = NOW()
                WHERE id = %s
                RETURNING id, display_name, description, model_id, sample_count, status,
                          created_at, updated_at
                """,
                (int(sample_count), model_id, status, profile_id),
            ).fetchone()
        return self._row_to_profile(row) if row else None

    @staticmethod
    def _row_to_profile(row: Any) -> VoiceprintProfile:
        status = str(row.get("status") or "pending")
        if status not in {"pending", "enrolled", "disabled"}:
            status = "pending"
        return VoiceprintProfile(
            id=str(row["id"]),
            display_name=str(row["display_name"]),
            description=str(row.get("description") or ""),
            model_id=str(row.get("model_id") or ""),
            sample_count=int(row.get("sample_count") or 0),
            status=status,  # type: ignore[arg-type]
            created_at=_iso(row.get("created_at")),
            updated_at=_iso(row.get("updated_at")),
        )

    @staticmethod
    def _row_to_sample(row: Any) -> VoiceprintSample:
        return VoiceprintSample(
            id=str(row["id"]),
            profile_id=str(row["profile_id"]),
            model_id=str(row.get("model_id") or ""),
            duration_ms=int(row.get("duration_ms") or 0),
            device_hint=str(row.get("device_hint") or ""),
            env_hint=str(row.get("env_hint") or ""),
            created_at=_iso(row.get("created_at")),
        )


_store: ProfileStore | None = None
_memory_fallback = InMemoryProfileStore()


def configure_profile_store(store: ProfileStore | None) -> None:
    global _store
    _store = store


def get_profile_store() -> ProfileStore:
    if _store is not None:
        return _store
    from app.persistence.bootstrap import get_sync_pool, is_postgres_enabled

    if is_postgres_enabled():
        try:
            return PostgresProfileStore(get_sync_pool())
        except Exception:  # noqa: BLE001
            logger.warning("声纹 Postgres 不可用，回退内存", exc_info=True)
    return _memory_fallback
