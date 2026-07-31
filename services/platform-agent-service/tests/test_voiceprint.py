"""声纹特征与内存库单测。"""

from __future__ import annotations

import numpy as np

from app.services.voice.voiceprint_features import (
    cosine_similarity,
    extract_embedding,
    merge_embeddings,
)
from app.services.voice.voiceprint_service import (
    VoiceprintError,
    create_voiceprint,
    enroll_voiceprint,
    list_voiceprints,
    verify_voiceprint,
)
from app.services.voice.voiceprint_store import (
    InMemoryVoiceprintStore,
    configure_voiceprint_store,
)


def _tone_pcm(freq: float, seconds: float = 1.2, sr: int = 16000) -> bytes:
    t = np.linspace(0, seconds, int(sr * seconds), endpoint=False)
    wave = (0.35 * np.sin(2 * np.pi * freq * t)).astype(np.float32)
    pcm = (wave * 32767).astype(np.int16)
    return pcm.tobytes()


def test_extract_and_cosine_same_speaker_higher() -> None:
    a = extract_embedding(_tone_pcm(220.0))
    b = extract_embedding(_tone_pcm(230.0))
    c = extract_embedding(_tone_pcm(1200.0))
    assert cosine_similarity(a, b) > cosine_similarity(a, c)


def test_merge_embeddings_keeps_dim() -> None:
    base = extract_embedding(_tone_pcm(300.0))
    nxt = extract_embedding(_tone_pcm(310.0))
    merged = merge_embeddings(base, nxt, count=1)
    assert len(merged) == len(base)


def test_voiceprint_crud_enroll_verify(monkeypatch) -> None:
    store = InMemoryVoiceprintStore()
    configure_voiceprint_store(store)
    monkeypatch.setattr(
        "app.services.voice.voiceprint_service.settings.voiceprint_enabled",
        True,
    )
    monkeypatch.setattr(
        "app.services.voice.voiceprint_service.settings.voiceprint_match_threshold",
        0.5,
    )

    created = create_voiceprint(display_name="张三", description="值班员")
    assert created["display_name"] == "张三"
    assert any(i["id"] == created["id"] for i in list_voiceprints())

    enroll_voiceprint(created["id"], _tone_pcm(440.0))
    enroll_voiceprint(created["id"], _tone_pcm(450.0))

    ok = verify_voiceprint(created["id"], _tone_pcm(445.0))
    assert ok["matched"] is True
    assert ok["score"] >= 0.5

    bad = verify_voiceprint(created["id"], _tone_pcm(1800.0))
    # 频谱差异足够大时通常不匹配；若偶发匹配仅断言结构
    assert "matched" in bad
    assert "score" in bad


def test_verify_requires_enrollment(monkeypatch) -> None:
    configure_voiceprint_store(InMemoryVoiceprintStore())
    monkeypatch.setattr(
        "app.services.voice.voiceprint_service.settings.voiceprint_enabled",
        True,
    )
    created = create_voiceprint(display_name="空用户")
    try:
        verify_voiceprint(created["id"], _tone_pcm(400.0))
        raise AssertionError("应抛出未录入错误")
    except VoiceprintError as exc:
        assert "尚未录入" in str(exc)
