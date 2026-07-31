"""声纹特征与内存库单测（默认 mock ECAPA，避免单测强依赖模型下载）。"""

from __future__ import annotations

import numpy as np
import pytest

from app.services.voice.voiceprint_features import (
    EMBEDDING_DIM,
    cosine_similarity,
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


def _fake_embedding_from_pcm(audio_bytes: bytes, *, sample_rate: int | None = None) -> list[float]:
    """用能量谱粗哈希生成确定性 192 维向量，便于门禁单测。"""
    del sample_rate
    samples = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
    if samples.size < 16:
        raise ValueError("音频过短")
    # 按频率桶取均值，映射到固定维
    n = EMBEDDING_DIM
    chunks = np.array_split(np.abs(samples), n)
    vec = np.array([float(np.mean(c)) if len(c) else 0.0 for c in chunks], dtype=np.float64)
    # 加入主导频率特征，拉开不同音调差异
    spec = np.abs(np.fft.rfft(samples[: min(len(samples), 4096)]))
    peak = int(np.argmax(spec))
    vec = vec + 0.01 * np.sin(np.linspace(0, peak, n))
    norm = float(np.linalg.norm(vec)) or 1.0
    return [float(x / norm) for x in vec.tolist()]


@pytest.fixture
def mock_ecapa(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "app.services.voice.voiceprint_service.extract_embedding",
        _fake_embedding_from_pcm,
    )


def test_merge_embeddings_keeps_dim() -> None:
    base = [1.0 / (EMBEDDING_DIM**0.5)] * EMBEDDING_DIM
    nxt = list(base)
    nxt[0], nxt[1] = nxt[1], nxt[0]
    merged = merge_embeddings(base, nxt, count=1)
    assert len(merged) == EMBEDDING_DIM
    assert abs(sum(x * x for x in merged) - 1.0) < 1e-5


def test_cosine_similarity_identity() -> None:
    v = [0.0] * EMBEDDING_DIM
    v[0] = 1.0
    assert cosine_similarity(v, v) == pytest.approx(1.0)
    assert cosine_similarity(v, [0.0] * 64) == 0.0


def test_voiceprint_crud_enroll_verify(monkeypatch: pytest.MonkeyPatch, mock_ecapa) -> None:
    del mock_ecapa
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
    assert "matched" in bad
    assert "score" in bad


def test_verify_requires_enrollment(monkeypatch: pytest.MonkeyPatch) -> None:
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


def test_verify_rejects_legacy_embedding_dim(monkeypatch: pytest.MonkeyPatch, mock_ecapa) -> None:
    del mock_ecapa
    store = InMemoryVoiceprintStore()
    configure_voiceprint_store(store)
    monkeypatch.setattr(
        "app.services.voice.voiceprint_service.settings.voiceprint_enabled",
        True,
    )
    created = create_voiceprint(display_name="旧模板")
    store.save_embedding(created["id"], embedding=[0.1] * 64, sample_count=1)
    try:
        verify_voiceprint(created["id"], _tone_pcm(400.0))
        raise AssertionError("应拒绝旧维度模板")
    except VoiceprintError as exc:
        assert "不兼容" in str(exc)


@pytest.mark.integration
def test_ecapa_extract_embedding_real_model() -> None:
    """需联网下载/已缓存 HuggingFace 权重；日常单测可跳过。"""
    from app.services.voice.voiceprint_features import extract_embedding

    emb = extract_embedding(_tone_pcm(220.0, seconds=1.5))
    assert len(emb) == EMBEDDING_DIM
    assert abs(sum(x * x for x in emb) - 1.0) < 1e-4
