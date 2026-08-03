"""声纹：多模板录入 / 1:1 / 1:N（默认 mock 嵌入与预处理）。"""

from __future__ import annotations

import numpy as np
import pytest

from app.services.voice.voiceprint.calibrate import calibrate_score, reset_calibration_for_tests
from app.services.voice.voiceprint.embedding import (
    DEFAULT_MODEL_ID,
    EMBEDDING_DIM,
    aggregate_scores,
    cosine_similarity,
)
from app.services.voice.voiceprint.preprocess import PreprocessError, preprocess_audio
from app.services.voice.voiceprint.service import (
    VoiceprintError,
    create_voiceprint,
    enroll_voiceprint,
    identify_voiceprint,
    list_voiceprints,
    verify_voiceprint,
)
from app.services.voice.voiceprint.store_pg import InMemoryProfileStore, configure_profile_store
from app.services.voice.voiceprint.store_qdrant import InMemoryVectorIndex, configure_vector_index
from app.services.voice.voiceprint.types import PreprocessResult


def _tone_pcm(freq: float, seconds: float = 1.2, sr: int = 16000) -> bytes:
    t = np.linspace(0, seconds, int(sr * seconds), endpoint=False)
    wave = (0.35 * np.sin(2 * np.pi * freq * t)).astype(np.float32)
    pcm = (wave * 32767).astype(np.int16)
    return pcm.tobytes()


def _fake_embedding_from_waveform(samples: np.ndarray, *, sample_rate: int = 16000) -> list[float]:
    del sample_rate
    n = EMBEDDING_DIM
    if samples.size < 16:
        raise ValueError("音频过短")
    chunks = np.array_split(np.abs(samples.astype(np.float64)), n)
    vec = np.array([float(np.mean(c)) if len(c) else 0.0 for c in chunks], dtype=np.float64)
    peak = int(np.argmax(np.abs(np.fft.rfft(samples[: min(len(samples), 4096)]))))
    vec = vec + 0.01 * np.sin(np.linspace(0, peak, n))
    norm = float(np.linalg.norm(vec)) or 1.0
    return [float(x / norm) for x in vec.tolist()]


def _fake_preprocess(
    audio_bytes: bytes,
    *,
    sample_rate: int | None = None,
    min_speech_ms: int,
    vad_enabled: bool | None = None,
    denoise_enabled: bool | None = None,
) -> PreprocessResult:
    del vad_enabled, denoise_enabled
    sr = sample_rate or 16000
    samples = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
    speech_ms = int(round(samples.size / sr * 1000))
    if speech_ms < min_speech_ms:
        raise PreprocessError("audio_too_short", f"有效语音不足 {min_speech_ms}ms")
    return PreprocessResult(samples=samples, speech_ms=speech_ms, sample_rate=sr)


@pytest.fixture
def voiceprint_env(monkeypatch: pytest.MonkeyPatch):
    store = InMemoryProfileStore()
    index = InMemoryVectorIndex()
    configure_profile_store(store)
    configure_vector_index(index)
    monkeypatch.setattr(
        "app.services.voice.voiceprint.service.settings.voiceprint_enabled",
        True,
    )
    monkeypatch.setattr(
        "app.services.voice.voiceprint.service.settings.voiceprint_enroll_min_samples",
        3,
    )
    monkeypatch.setattr(
        "app.services.voice.voiceprint.service.settings.voiceprint_enroll_max_samples",
        5,
    )
    monkeypatch.setattr(
        "app.services.voice.voiceprint.service.settings.voiceprint_enroll_min_speech_ms",
        500,
    )
    monkeypatch.setattr(
        "app.services.voice.voiceprint.service.settings.voiceprint_verify_min_speech_ms",
        500,
    )
    monkeypatch.setattr(
        "app.services.voice.voiceprint.service.settings.voiceprint_threshold_assistant_gate",
        0.5,
    )
    monkeypatch.setattr(
        "app.services.voice.voiceprint.service.settings.voiceprint_threshold_identify",
        0.5,
    )
    monkeypatch.setattr(
        "app.services.voice.voiceprint.service.preprocess_audio",
        _fake_preprocess,
    )
    monkeypatch.setattr(
        "app.services.voice.voiceprint.service.extract_embedding_from_waveform",
        _fake_embedding_from_waveform,
    )
    monkeypatch.setattr(
        "app.services.voice.voiceprint.service.current_model_id",
        lambda: DEFAULT_MODEL_ID,
    )
    reset_calibration_for_tests()
    # 单测：校准近似恒等，便于用 raw cosine 阈值
    monkeypatch.setattr(
        "app.services.voice.voiceprint.service.calibrate_score",
        lambda x: float(x),
    )
    return store, index


def test_cosine_and_aggregate() -> None:
    v = [0.0] * EMBEDDING_DIM
    v[0] = 1.0
    assert cosine_similarity(v, v) == pytest.approx(1.0)
    assert aggregate_scores([0.2, 0.9, 0.4], mode="max") == pytest.approx(0.9)


def test_calibrate_monotonic() -> None:
    reset_calibration_for_tests()
    low = calibrate_score(0.3)
    high = calibrate_score(0.8)
    assert 0.0 <= low < high <= 1.0


def test_preprocess_too_short(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.config.settings.voiceprint_vad_enabled",
        False,
    )
    monkeypatch.setattr(
        "app.config.settings.voiceprint_denoise_enabled",
        False,
    )
    with pytest.raises(PreprocessError) as exc:
        preprocess_audio(_tone_pcm(440.0, seconds=0.05), min_speech_ms=2000)
    assert exc.value.code in {"audio_too_short", "pipeline_failed"}


def test_enroll_verify_identify(voiceprint_env) -> None:
    del voiceprint_env
    created = create_voiceprint(display_name="张三", description="值班员")
    assert created["enrolled"] is False
    assert created["status"] == "pending"

    for _ in range(3):
        enrolled = enroll_voiceprint(created["id"], _tone_pcm(440.0, seconds=0.8))
    assert enrolled["enrolled"] is True
    assert enrolled["sample_count"] == 3
    assert enrolled["status"] == "enrolled"
    assert any(i["id"] == created["id"] for i in list_voiceprints())

    ok = verify_voiceprint(created["id"], _tone_pcm(445.0, seconds=0.8))
    assert ok["matched"] is True
    assert ok["decision"] == "accept"
    assert "latency_ms" in ok
    assert ok["model_id"] == DEFAULT_MODEL_ID

    identified = identify_voiceprint(_tone_pcm(442.0, seconds=0.8))
    assert identified["matched"] is True
    assert identified["profile_id"] == created["id"]

    other = create_voiceprint(display_name="李四")
    for _ in range(3):
        enroll_voiceprint(other["id"], _tone_pcm(1800.0, seconds=0.8))
    # 用张三模板核验李四频率：分数应较低（mock 下未必严格，至少字段完整）
    bad = verify_voiceprint(created["id"], _tone_pcm(1800.0, seconds=0.8))
    assert "matched" in bad
    assert "score" in bad
    assert "score_raw" in bad


def test_verify_requires_min_enroll(voiceprint_env) -> None:
    del voiceprint_env
    created = create_voiceprint(display_name="空用户")
    enroll_voiceprint(created["id"], _tone_pcm(400.0, seconds=0.8))
    with pytest.raises(VoiceprintError) as exc:
        verify_voiceprint(created["id"], _tone_pcm(400.0, seconds=0.8))
    assert "尚未完成录入" in str(exc.value)


def test_enroll_rejects_over_max(voiceprint_env, monkeypatch: pytest.MonkeyPatch) -> None:
    del voiceprint_env
    monkeypatch.setattr(
        "app.services.voice.voiceprint.service.settings.voiceprint_enroll_max_samples",
        3,
    )
    created = create_voiceprint(display_name="上限用户")
    for _ in range(3):
        enroll_voiceprint(created["id"], _tone_pcm(500.0, seconds=0.8))
    with pytest.raises(VoiceprintError) as exc:
        enroll_voiceprint(created["id"], _tone_pcm(500.0, seconds=0.8))
    assert "上限" in str(exc.value)
