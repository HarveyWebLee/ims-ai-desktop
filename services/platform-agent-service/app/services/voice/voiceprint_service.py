"""声纹业务：录入、核验（FunASR ERes2NetV2）。"""

from __future__ import annotations

from typing import Any

from app.config import settings
from app.services.voice.voiceprint_features import (
    EMBEDDING_DIM,
    cosine_similarity,
    current_model_id,
    extract_embedding,
    merge_embeddings,
)
from app.services.voice.voiceprint_store import VoiceprintProfile, get_voiceprint_store


class VoiceprintError(Exception):
    """声纹业务错误。"""


def _public(profile: VoiceprintProfile) -> dict[str, Any]:
    return profile.to_public_dict(current_model_id=current_model_id())


def list_voiceprints() -> list[dict[str, Any]]:
    mid = current_model_id()
    return [p.to_public_dict(current_model_id=mid) for p in get_voiceprint_store().list_profiles()]


def create_voiceprint(*, display_name: str, description: str = "") -> dict[str, Any]:
    name = (display_name or "").strip()
    if not name:
        raise VoiceprintError("显示名称不能为空")
    profile = get_voiceprint_store().create(display_name=name, description=description)
    return _public(profile)


def update_voiceprint(
    profile_id: str,
    *,
    display_name: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    profile = get_voiceprint_store().update(
        profile_id,
        display_name=display_name,
        description=description,
    )
    if profile is None:
        raise VoiceprintError("声纹用户不存在")
    return _public(profile)


def delete_voiceprint(profile_id: str) -> None:
    if not get_voiceprint_store().delete(profile_id):
        raise VoiceprintError("声纹用户不存在")


def enroll_voiceprint(
    profile_id: str,
    audio_bytes: bytes,
    *,
    sample_rate: int | None = None,
) -> dict[str, Any]:
    store = get_voiceprint_store()
    profile = store.get(profile_id)
    if profile is None:
        raise VoiceprintError("声纹用户不存在")
    try:
        incoming = extract_embedding(audio_bytes, sample_rate=sample_rate)
    except ValueError as exc:
        raise VoiceprintError(str(exc)) from exc

    model_id = current_model_id()
    # 旧 ECAPA / 其它 model_id / 非当前维度：重新累计
    prior_count = profile.sample_count
    prior_emb = profile.embedding
    if prior_emb and (len(prior_emb) != EMBEDDING_DIM or (profile.model_id or "") != model_id):
        prior_count = 0
        prior_emb = None

    merged = merge_embeddings(prior_emb, incoming, count=prior_count)
    updated = store.save_embedding(
        profile_id,
        embedding=merged,
        sample_count=prior_count + 1,
        model_id=model_id,
    )
    if updated is None:
        raise VoiceprintError("声纹用户不存在")
    return _public(updated)


def verify_voiceprint(
    profile_id: str,
    audio_bytes: bytes,
    *,
    sample_rate: int | None = None,
) -> dict[str, Any]:
    if not settings.voiceprint_enabled:
        return {
            "matched": True,
            "score": 1.0,
            "threshold": float(settings.voiceprint_match_threshold),
            "skipped": True,
            "reason": "voiceprint_disabled",
        }
    store = get_voiceprint_store()
    profile = store.get(profile_id)
    if profile is None:
        raise VoiceprintError("声纹用户不存在")
    if profile.sample_count <= 0 or not profile.embedding:
        raise VoiceprintError("该用户尚未录入声纹，请先完成录入")
    model_id = current_model_id()
    if (profile.model_id or "") != model_id or len(profile.embedding) != EMBEDDING_DIM:
        raise VoiceprintError("声纹模板与当前 ERes2Net 算法不兼容，请重新录入")
    try:
        probe = extract_embedding(audio_bytes, sample_rate=sample_rate)
    except ValueError as exc:
        raise VoiceprintError(str(exc)) from exc
    score = cosine_similarity(profile.embedding, probe)
    threshold = float(settings.voiceprint_match_threshold)
    return {
        "matched": score >= threshold,
        "score": round(score, 4),
        "threshold": threshold,
        "profile_id": profile.id,
        "display_name": profile.display_name,
        "model_id": model_id,
        "skipped": False,
    }


def get_profile(profile_id: str) -> VoiceprintProfile | None:
    return get_voiceprint_store().get(profile_id)
