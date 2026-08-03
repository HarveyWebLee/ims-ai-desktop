"""声纹特征：FunASR + ModelScope ERes2NetV2 说话人嵌入。"""

from __future__ import annotations

import logging
import math
import struct
import tempfile
import threading
import wave
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

# iic/speech_eres2netv2_sv_zh-cn_16k-common 输出 192 维
EMBEDDING_DIM = 192
_TARGET_SR = 16000
DEFAULT_MODEL_ID = "iic/speech_eres2netv2_sv_zh-cn_16k-common"

logger = logging.getLogger(__name__)

_model_lock = threading.Lock()
_sv_model: Any | None = None
_sv_model_id: str | None = None


def current_model_id() -> str:
    from app.config import settings

    configured = (settings.voiceprint_model_id or "").strip()
    return configured or DEFAULT_MODEL_ID


def _pcm16_mono_samples(
    audio_bytes: bytes, *, sample_rate: int | None = None
) -> tuple[np.ndarray, int]:
    """解析 PCM16 LE 或带 WAV 头的音频为 float32 mono 波形。"""
    raw = audio_bytes
    sr = sample_rate or _TARGET_SR
    if len(raw) >= 44 and raw[:4] == b"RIFF" and raw[8:12] == b"WAVE":
        idx = 12
        data = b""
        while idx + 8 <= len(raw):
            chunk_id = raw[idx : idx + 4]
            chunk_size = struct.unpack_from("<I", raw, idx + 4)[0]
            idx += 8
            payload = raw[idx : idx + chunk_size]
            idx += chunk_size
            if chunk_id == b"fmt " and len(payload) >= 16:
                _, channels, sr, _, _, bits = struct.unpack_from("<HHIIHH", payload, 0)
                if channels != 1 or bits != 16:
                    raise ValueError("仅支持 16bit 单声道 WAV/PCM")
            elif chunk_id == b"data":
                data = payload
                break
        if not data:
            raise ValueError("WAV 中未找到 data 块")
        raw = data
    if len(raw) < 3200:  # <0.1s @16k
        raise ValueError("音频过短，请至少录制 1 秒以上")
    if len(raw) % 2:
        raw = raw[:-1]
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if sample_rate and sample_rate != _TARGET_SR and sample_rate > 0:
        duration = len(samples) / float(sample_rate)
        target_len = max(1, int(duration * _TARGET_SR))
        x_old = np.linspace(0.0, 1.0, num=len(samples), endpoint=False)
        x_new = np.linspace(0.0, 1.0, num=target_len, endpoint=False)
        samples = np.interp(x_new, x_old, samples).astype(np.float32)
        sr = _TARGET_SR
    return samples, sr


def _write_wav_pcm16(path: Path, samples: np.ndarray, *, sample_rate: int) -> None:
    pcm = np.clip(samples * 32767.0, -32768, 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())


def _resolve_device() -> str:
    import torch

    from app.config import settings

    configured = (settings.voiceprint_device or "").strip().lower()
    if configured in {"cpu", "cuda"}:
        if configured == "cuda" and not torch.cuda.is_available():
            logger.warning("VOICEPRINT_DEVICE=cuda 但 CUDA 不可用，回退 CPU")
            return "cpu"
        return configured
    return "cuda" if torch.cuda.is_available() else "cpu"


def get_sv_model() -> Any:
    """懒加载 FunASR ERes2NetV2（进程内单例；model_id 变更时重建）。"""
    global _sv_model, _sv_model_id
    model_id = current_model_id()
    if _sv_model is not None and _sv_model_id == model_id:
        return _sv_model
    with _model_lock:
        if _sv_model is not None and _sv_model_id == model_id:
            return _sv_model
        from funasr import AutoModel

        device = _resolve_device()
        logger.info("加载 ERes2Net 声纹模型 model_id=%s device=%s", model_id, device)
        loaded = AutoModel(model=model_id, device=device, disable_update=True)
        if loaded is None:
            raise RuntimeError("ERes2Net 声纹模型加载失败")
        _sv_model = loaded
        _sv_model_id = model_id
        return loaded


def reset_sv_model_for_tests() -> None:
    """测试用：清空已加载模型。"""
    global _sv_model, _sv_model_id
    with _model_lock:
        _sv_model = None
        _sv_model_id = None


def extract_embedding(
    audio_bytes: bytes,
    *,
    sample_rate: int | None = None,
) -> list[float]:
    """
    从 PCM/WAV 提取 L2 归一化 ERes2Net 说话人嵌入（默认 192 维）。

    首次调用会从 ModelScope 拉取预训练权重到本地缓存。
    """
    samples, sr = _pcm16_mono_samples(audio_bytes, sample_rate=sample_rate)
    energy = float(np.sqrt(np.mean(np.square(samples))))
    if energy < 1e-4:
        raise ValueError("音频能量过低，请靠近麦克风重新录入")

    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        _write_wav_pcm16(tmp_path, samples, sample_rate=sr if sr > 0 else _TARGET_SR)

        model = get_sv_model()
        with _model_lock:
            raw = model.generate(input=str(tmp_path))
        if not raw or not isinstance(raw, list) or "spk_embedding" not in raw[0]:
            raise ValueError("无法从音频提取有效声纹特征")
        emb = raw[0]["spk_embedding"]
        if hasattr(emb, "detach"):
            emb = emb.detach().cpu().numpy()
        vec = np.asarray(emb, dtype=np.float64).reshape(-1)
        if vec.size != EMBEDDING_DIM:
            if vec.size > EMBEDDING_DIM:
                vec = vec[:EMBEDDING_DIM]
            else:
                vec = np.pad(vec, (0, EMBEDDING_DIM - vec.size))
        norm = float(np.linalg.norm(vec))
        if norm < 1e-8:
            raise ValueError("无法从音频提取有效声纹特征")
        vec = vec / norm
        return [float(x) for x in vec.tolist()]
    finally:
        if tmp_path is not None:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                logger.debug("清理临时声纹 WAV 失败 path=%s", tmp_path, exc_info=True)


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    va = np.asarray(a, dtype=np.float64)
    vb = np.asarray(b, dtype=np.float64)
    na = float(np.linalg.norm(va))
    nb = float(np.linalg.norm(vb))
    if na < 1e-12 or nb < 1e-12:
        return 0.0
    return float(np.dot(va, vb) / (na * nb))


def merge_embeddings(
    existing: Sequence[float] | None, incoming: Sequence[float], *, count: int
) -> list[float]:
    """把新样本嵌入并入已有声纹（在线均值）。"""
    if not existing or count <= 0:
        return [float(x) for x in incoming]
    n = max(1, count)
    merged = [(float(e) * n + float(i)) / (n + 1) for e, i in zip(existing, incoming, strict=False)]
    if len(merged) < EMBEDDING_DIM:
        merged.extend([0.0] * (EMBEDDING_DIM - len(merged)))
    merged = merged[:EMBEDDING_DIM]
    norm = math.sqrt(sum(x * x for x in merged)) or 1.0
    return [x / norm for x in merged]
