"""场景阈值与 accept / unknown 决策。"""

from __future__ import annotations

from app.config import settings
from app.services.voice.voiceprint.types import Decision, Scene


def resolve_scene(scene: str | None, *, default: Scene) -> Scene:
    raw = (scene or "").strip().lower()
    if raw in {"assistant_gate", "meeting", "identify_open"}:
        return raw  # type: ignore[return-value]
    return default


def threshold_for_scene(scene: Scene) -> float:
    if scene == "meeting":
        return float(settings.voiceprint_threshold_meeting)
    if scene == "identify_open":
        return float(settings.voiceprint_threshold_identify)
    return float(settings.voiceprint_threshold_assistant_gate)


def decide(*, score: float, threshold: float, open_set: bool) -> Decision:
    if score >= threshold:
        return "accept"
    return "unknown" if open_set else "reject"
