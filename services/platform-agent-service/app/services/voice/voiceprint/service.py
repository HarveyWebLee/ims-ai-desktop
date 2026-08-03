"""声纹业务：多模板录入、1:1 核验、1:N 识别。"""

from __future__ import annotations

import time
import uuid
from typing import Any

from app.config import settings
from app.services.voice.voiceprint.cache_redis import (
    cache_embeddings,
    get_cached_embeddings,
    invalidate_profile,
)
from app.services.voice.voiceprint.calibrate import calibrate_score
from app.services.voice.voiceprint.decision import decide, resolve_scene, threshold_for_scene
from app.services.voice.voiceprint.embedding import (
    aggregate_scores,
    cosine_similarity,
    current_model_id,
    extract_embedding_from_waveform,
)
from app.services.voice.voiceprint.metrics import log_voiceprint_event
from app.services.voice.voiceprint.preprocess import PreprocessError, preprocess_audio
from app.services.voice.voiceprint.store_pg import get_profile_store
from app.services.voice.voiceprint.store_qdrant import get_vector_index
from app.services.voice.voiceprint.types import LatencyMs, MatchResult, ProfileStatus


class VoiceprintError(Exception):
    """声纹业务错误。"""


def _enroll_min() -> int:
    return max(1, int(settings.voiceprint_enroll_min_samples or 3))


def _enroll_max() -> int:
    return max(_enroll_min(), int(settings.voiceprint_enroll_max_samples or 5))


def _public(profile: Any) -> dict[str, Any]:
    return profile.to_public_dict(enroll_min=_enroll_min())


def list_voiceprints() -> list[dict[str, Any]]:
    return [_public(p) for p in get_profile_store().list_profiles()]


def create_voiceprint(*, display_name: str, description: str = "") -> dict[str, Any]:
    name = (display_name or "").strip()
    if not name:
        raise VoiceprintError("显示名称不能为空")
    profile = get_profile_store().create(display_name=name, description=description)
    return _public(profile)


def update_voiceprint(
    profile_id: str,
    *,
    display_name: str | None = None,
    description: str | None = None,
    status: ProfileStatus | None = None,
) -> dict[str, Any]:
    profile = get_profile_store().update(
        profile_id,
        display_name=display_name,
        description=description,
        status=status,
    )
    if profile is None:
        raise VoiceprintError("声纹用户不存在")
    invalidate_profile(profile_id)
    return _public(profile)


def delete_voiceprint(profile_id: str) -> None:
    store = get_profile_store()
    if store.get(profile_id) is None:
        raise VoiceprintError("声纹用户不存在")
    get_vector_index().delete_profile(profile_id)
    invalidate_profile(profile_id)
    if not store.delete(profile_id):
        raise VoiceprintError("声纹用户不存在")


def list_samples(profile_id: str) -> list[dict[str, Any]]:
    store = get_profile_store()
    if store.get(profile_id) is None:
        raise VoiceprintError("声纹用户不存在")
    return [
        {
            "id": s.id,
            "profile_id": s.profile_id,
            "model_id": s.model_id,
            "duration_ms": s.duration_ms,
            "device_hint": s.device_hint,
            "env_hint": s.env_hint,
            "created_at": s.created_at,
        }
        for s in store.list_samples(profile_id)
    ]


def _refresh_profile_status(profile_id: str, *, model_id: str) -> Any:
    store = get_profile_store()
    samples = store.list_samples(profile_id)
    count = len(samples)
    status: ProfileStatus = "enrolled" if count >= _enroll_min() else "pending"
    updated = store.set_counts(
        profile_id,
        sample_count=count,
        model_id=model_id if count > 0 else "",
        status=status,
    )
    invalidate_profile(profile_id)
    return updated


def delete_sample(profile_id: str, sample_id: str) -> dict[str, Any]:
    store = get_profile_store()
    profile = store.get(profile_id)
    if profile is None:
        raise VoiceprintError("声纹用户不存在")
    if not store.delete_sample(profile_id, sample_id):
        raise VoiceprintError("声纹样本不存在")
    get_vector_index().delete_sample(sample_id)
    updated = _refresh_profile_status(profile_id, model_id=current_model_id())
    if updated is None:
        raise VoiceprintError("声纹用户不存在")
    return _public(updated)


def _extract_probe(
    audio_bytes: bytes,
    *,
    sample_rate: int | None,
    min_speech_ms: int,
) -> tuple[list[float], int, LatencyMs]:
    latency = LatencyMs()
    t0 = time.perf_counter()
    try:
        prepared = preprocess_audio(
            audio_bytes,
            sample_rate=sample_rate,
            min_speech_ms=min_speech_ms,
        )
    except PreprocessError as exc:
        raise VoiceprintError(str(exc)) from exc
    latency.preprocess = (time.perf_counter() - t0) * 1000
    t1 = time.perf_counter()
    try:
        emb = extract_embedding_from_waveform(
            prepared.samples,
            sample_rate=prepared.sample_rate,
        )
    except ValueError as exc:
        raise VoiceprintError(str(exc)) from exc
    latency.embedding = (time.perf_counter() - t1) * 1000
    return emb, prepared.speech_ms, latency


def enroll_voiceprint(
    profile_id: str,
    audio_bytes: bytes,
    *,
    sample_rate: int | None = None,
    device_hint: str = "",
    env_hint: str = "",
) -> dict[str, Any]:
    store = get_profile_store()
    profile = store.get(profile_id)
    if profile is None:
        raise VoiceprintError("声纹用户不存在")
    if profile.status == "disabled":
        raise VoiceprintError("声纹用户已禁用")
    if profile.sample_count >= _enroll_max():
        raise VoiceprintError(f"已达录入上限 {_enroll_max()} 段，请先删除旧样本")

    model_id = current_model_id()
    # 模型切换：清空旧模板（破坏性，无兼容）
    if profile.model_id and profile.model_id != model_id and profile.sample_count > 0:
        get_vector_index().delete_profile(profile_id)
        for sample in store.list_samples(profile_id):
            store.delete_sample(profile_id, sample.id)
        store.set_counts(profile_id, sample_count=0, model_id="", status="pending")
        invalidate_profile(profile_id)

    emb, speech_ms, latency = _extract_probe(
        audio_bytes,
        sample_rate=sample_rate,
        min_speech_ms=int(settings.voiceprint_enroll_min_speech_ms or 8000),
    )
    sample_id = uuid.uuid4().hex
    sample = store.add_sample(
        profile_id,
        sample_id=sample_id,
        model_id=model_id,
        duration_ms=speech_ms,
        device_hint=device_hint,
        env_hint=env_hint,
    )
    if sample is None:
        raise VoiceprintError("声纹用户不存在")

    t_search = time.perf_counter()
    get_vector_index().upsert(
        sample_id=sample_id,
        embedding=emb,
        profile_id=profile_id,
        display_name=profile.display_name,
        model_id=model_id,
        device_hint=device_hint,
        env_hint=env_hint,
    )
    latency.search = (time.perf_counter() - t_search) * 1000
    latency.total = latency.preprocess + latency.embedding + latency.search

    updated = _refresh_profile_status(profile_id, model_id=model_id)
    if updated is None:
        raise VoiceprintError("声纹用户不存在")

    # 刷新缓存
    vectors = get_vector_index().list_by_profile(profile_id)
    cache_embeddings(
        profile_id,
        [v for _, v in vectors],
        {
            "display_name": updated.display_name,
            "sample_count": updated.sample_count,
            "model_id": updated.model_id,
        },
    )
    log_voiceprint_event(
        "voiceprint_enroll",
        profile_id=profile_id,
        sample_id=sample_id,
        model_id=model_id,
        vad_speech_ms=speech_ms,
        ms_preprocess=int(latency.preprocess),
        ms_embedding=int(latency.embedding),
        ms_search=int(latency.search),
        ms_total=int(latency.total),
        sample_count=updated.sample_count,
    )
    return _public(updated)


def _templates_for_profile(profile_id: str) -> list[list[float]]:
    cached = get_cached_embeddings(profile_id)
    if cached is not None:
        return cached
    pairs = get_vector_index().list_by_profile(profile_id)
    vectors = [v for _, v in pairs]
    if vectors:
        cache_embeddings(profile_id, vectors, {"profile_id": profile_id})
    return vectors


def verify_voiceprint(
    profile_id: str,
    audio_bytes: bytes,
    *,
    sample_rate: int | None = None,
    scene: str | None = None,
) -> dict[str, Any]:
    if not settings.voiceprint_enabled:
        return MatchResult(
            matched=True,
            decision="accept",
            score=1.0,
            score_raw=1.0,
            threshold=threshold_for_scene("assistant_gate"),
            profile_id=profile_id,
            display_name=None,
            model_id=current_model_id(),
            skipped=True,
            reason="voiceprint_disabled",
        ).to_dict()

    store = get_profile_store()
    profile = store.get(profile_id)
    if profile is None:
        raise VoiceprintError("声纹用户不存在")
    if profile.status == "disabled":
        raise VoiceprintError("声纹用户已禁用")
    if profile.sample_count < _enroll_min() or profile.status != "enrolled":
        raise VoiceprintError(f"该用户尚未完成录入（至少 {_enroll_min()} 段），请先完成录入")
    model_id = current_model_id()
    if (profile.model_id or "") != model_id:
        raise VoiceprintError("声纹模板与当前模型不一致，请重新录入")

    resolved = resolve_scene(scene, default="assistant_gate")
    threshold = threshold_for_scene(resolved)
    emb, speech_ms, latency = _extract_probe(
        audio_bytes,
        sample_rate=sample_rate,
        min_speech_ms=int(settings.voiceprint_verify_min_speech_ms or 2000),
    )

    t_search = time.perf_counter()
    templates = _templates_for_profile(profile_id)
    latency.search = (time.perf_counter() - t_search) * 1000
    if not templates:
        raise VoiceprintError("未找到声纹模板向量，请重新录入")

    scores = [cosine_similarity(emb, t) for t in templates]
    score_raw = aggregate_scores(scores, mode=(settings.voiceprint_score_agg or "max"))
    score = calibrate_score(score_raw)
    decision = decide(score=score, threshold=threshold, open_set=False)
    matched = decision == "accept"
    latency.total = latency.preprocess + latency.embedding + latency.search

    result = MatchResult(
        matched=matched,
        decision=decision,
        score=score,
        score_raw=score_raw,
        threshold=threshold,
        profile_id=profile.id,
        display_name=profile.display_name,
        model_id=model_id,
        latency_ms=latency,
        vad_speech_ms=speech_ms,
    )
    log_voiceprint_event(
        "voiceprint_verify",
        profile_id=profile_id,
        model_id=model_id,
        scene=resolved,
        score_raw=round(score_raw, 4),
        score=round(score, 4),
        threshold=threshold,
        decision=decision,
        ms_preprocess=int(latency.preprocess),
        ms_embedding=int(latency.embedding),
        ms_search=int(latency.search),
        ms_total=int(latency.total),
        vad_speech_ms=speech_ms,
    )
    return result.to_dict()


def identify_voiceprint(
    audio_bytes: bytes,
    *,
    sample_rate: int | None = None,
    scene: str | None = None,
    top_k: int | None = None,
) -> dict[str, Any]:
    if not settings.voiceprint_enabled:
        return MatchResult(
            matched=False,
            decision="unknown",
            score=0.0,
            score_raw=0.0,
            threshold=threshold_for_scene("identify_open"),
            profile_id=None,
            display_name=None,
            model_id=current_model_id(),
            skipped=True,
            reason="voiceprint_disabled",
        ).to_dict()

    resolved = resolve_scene(scene, default="identify_open")
    threshold = threshold_for_scene(resolved)
    k = max(1, int(top_k or settings.voiceprint_search_top_k or 20))
    emb, speech_ms, latency = _extract_probe(
        audio_bytes,
        sample_rate=sample_rate,
        min_speech_ms=int(settings.voiceprint_verify_min_speech_ms or 2000),
    )

    t_search = time.perf_counter()
    hits = get_vector_index().search(emb, top_k=k)
    latency.search = (time.perf_counter() - t_search) * 1000

    by_profile: dict[str, tuple[float, str]] = {}
    for hit in hits:
        if not hit.profile_id:
            continue
        prev = by_profile.get(hit.profile_id)
        if prev is None or hit.score > prev[0]:
            by_profile[hit.profile_id] = (hit.score, hit.display_name)

    best_id: str | None = None
    best_name: str | None = None
    score_raw = 0.0
    if by_profile:
        best_id, (score_raw, best_name) = max(by_profile.items(), key=lambda item: item[1][0])

    score = calibrate_score(score_raw) if best_id else 0.0
    decision = decide(score=score, threshold=threshold, open_set=True)
    matched = decision == "accept"
    if not matched:
        best_id = None
        best_name = None
    latency.total = latency.preprocess + latency.embedding + latency.search

    result = MatchResult(
        matched=matched,
        decision=decision if matched else "unknown",
        score=score,
        score_raw=score_raw,
        threshold=threshold,
        profile_id=best_id,
        display_name=best_name,
        model_id=current_model_id(),
        latency_ms=latency,
        vad_speech_ms=speech_ms,
        top_k=k,
    )
    log_voiceprint_event(
        "voiceprint_identify",
        profile_id=best_id,
        model_id=current_model_id(),
        scene=resolved,
        score_raw=round(score_raw, 4),
        score=round(score, 4),
        threshold=threshold,
        decision=result.decision,
        ms_preprocess=int(latency.preprocess),
        ms_embedding=int(latency.embedding),
        ms_search=int(latency.search),
        ms_total=int(latency.total),
        vad_speech_ms=speech_ms,
        top_k=k,
    )
    return result.to_dict()


def probe_voiceprint() -> dict[str, Any]:
    from app.services.voice.voiceprint.embedding import model_loaded
    from app.services.voice.voiceprint.store_qdrant import QdrantVectorIndex, get_vector_index

    index = get_vector_index()
    qdrant_ok = False
    if isinstance(index, QdrantVectorIndex):
        qdrant_ok = index.collection_exists()
    else:
        qdrant_ok = True
    return {
        "enabled": bool(settings.voiceprint_enabled),
        "model_id": current_model_id(),
        "model_loaded": model_loaded(),
        "qdrant_collection": settings.voiceprint_qdrant_collection,
        "qdrant_ok": qdrant_ok,
        "embedding_dim": int(settings.voiceprint_embedding_dim or 512),
    }
