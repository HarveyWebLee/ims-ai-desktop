"""声纹领域类型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

ProfileStatus = Literal["pending", "enrolled", "disabled"]
Decision = Literal["accept", "unknown", "reject"]
Scene = Literal["assistant_gate", "meeting", "identify_open"]


@dataclass
class VoiceprintProfile:
    id: str
    display_name: str
    description: str = ""
    model_id: str = ""
    sample_count: int = 0
    status: ProfileStatus = "pending"
    created_at: str = ""
    updated_at: str = ""

    def to_public_dict(self, *, enroll_min: int) -> dict[str, Any]:
        enrolled = self.status == "enrolled" and self.sample_count >= enroll_min
        return {
            "id": self.id,
            "display_name": self.display_name,
            "description": self.description,
            "sample_count": self.sample_count,
            "status": self.status,
            "enrolled": enrolled,
            "model_id": self.model_id,
            "enroll_min": enroll_min,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class VoiceprintSample:
    id: str
    profile_id: str
    model_id: str
    duration_ms: int = 0
    device_hint: str = ""
    env_hint: str = ""
    created_at: str = ""


@dataclass
class LatencyMs:
    preprocess: float = 0.0
    embedding: float = 0.0
    search: float = 0.0
    total: float = 0.0

    def to_dict(self) -> dict[str, int]:
        return {
            "preprocess": int(round(self.preprocess)),
            "embedding": int(round(self.embedding)),
            "search": int(round(self.search)),
            "total": int(round(self.total)),
        }


@dataclass
class PreprocessResult:
    samples: Any  # np.ndarray float32
    speech_ms: int
    sample_rate: int = 16000


@dataclass
class MatchResult:
    matched: bool
    decision: Decision
    score: float
    score_raw: float
    threshold: float
    profile_id: str | None
    display_name: str | None
    model_id: str
    latency_ms: LatencyMs = field(default_factory=LatencyMs)
    skipped: bool = False
    reason: str = ""
    vad_speech_ms: int = 0
    top_k: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "matched": self.matched,
            "decision": self.decision,
            "score": round(self.score, 4),
            "score_raw": round(self.score_raw, 4),
            "threshold": self.threshold,
            "profile_id": self.profile_id,
            "display_name": self.display_name,
            "model_id": self.model_id,
            "latency_ms": self.latency_ms.to_dict(),
            "skipped": self.skipped,
            "reason": self.reason,
            "vad_speech_ms": self.vad_speech_ms,
            "top_k": self.top_k,
        }
