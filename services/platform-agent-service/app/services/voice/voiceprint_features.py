"""声纹特征：SpeechBrain ECAPA-TDNN 说话人嵌入。"""

from __future__ import annotations

import logging
import math
import struct
import threading
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
import torch

# speechbrain/spkrec-ecapa-voxceleb 输出 192 维
EMBEDDING_DIM = 192
_TARGET_SR = 16000

logger = logging.getLogger(__name__)

_classifier_lock = threading.Lock()
_classifier: Any | None = None


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


def _resolve_savedir() -> Path:
    from app.config import settings

    configured = (settings.voiceprint_ecapa_savedir or "").strip()
    if configured:
        path = Path(configured)
    else:
        path = Path(settings.agent_data_dir) / "pretrained" / "spkrec-ecapa-voxceleb"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _resolve_device() -> str:
    from app.config import settings

    configured = (settings.voiceprint_ecapa_device or "").strip().lower()
    if configured in {"cpu", "cuda"}:
        if configured == "cuda" and not torch.cuda.is_available():
            logger.warning("VOICEPRINT_ECAPA_DEVICE=cuda 但 CUDA 不可用，回退 CPU")
            return "cpu"
        return configured
    return "cuda" if torch.cuda.is_available() else "cpu"


def get_ecapa_classifier() -> Any:
    """懒加载 SpeechBrain ECAPA EncoderClassifier（进程内单例）。"""
    global _classifier
    if _classifier is not None:
        return _classifier
    with _classifier_lock:
        if _classifier is not None:
            return _classifier
        from speechbrain.inference.speaker import EncoderClassifier
        from speechbrain.utils.fetching import LocalStrategy

        from app.config import settings

        source = (settings.voiceprint_ecapa_source or "").strip() or (
            "speechbrain/spkrec-ecapa-voxceleb"
        )
        savedir = _resolve_savedir()
        device = _resolve_device()
        logger.info(
            "加载 ECAPA 声纹模型 source=%s savedir=%s device=%s",
            source,
            savedir,
            device,
        )
        # Windows 无管理员/开发者模式时无法创建 symlink，改用 COPY
        loaded = EncoderClassifier.from_hparams(
            source=source,
            savedir=str(savedir),
            run_opts={"device": device},
            local_strategy=LocalStrategy.COPY,
        )
        if loaded is None:
            raise RuntimeError("ECAPA 声纹模型加载失败")
        loaded.eval()
        _classifier = loaded
        return loaded


def reset_ecapa_classifier_for_tests() -> None:
    """测试用：清空已加载模型。"""
    global _classifier
    with _classifier_lock:
        _classifier = None


def extract_embedding(
    audio_bytes: bytes,
    *,
    sample_rate: int | None = None,
) -> list[float]:
    """
    从 PCM/WAV 提取 L2 归一化 ECAPA 说话人嵌入（192 维）。

    首次调用会从 Hugging Face 拉取预训练权重到本地 savedir。
    """
    samples, _sr = _pcm16_mono_samples(audio_bytes, sample_rate=sample_rate)
    energy = float(np.sqrt(np.mean(np.square(samples))))
    if energy < 1e-4:
        raise ValueError("音频能量过低，请靠近麦克风重新录入")

    waveform = torch.from_numpy(samples).unsqueeze(0)  # [1, time]
    classifier = get_ecapa_classifier()
    with torch.inference_mode():
        emb = classifier.encode_batch(waveform)
    vec = emb.squeeze().detach().cpu().float().numpy().reshape(-1)
    if vec.size != EMBEDDING_DIM:
        # 兼容少数自定义 checkpoint 维度
        if vec.size > EMBEDDING_DIM:
            vec = vec[:EMBEDDING_DIM]
        else:
            vec = np.pad(vec, (0, EMBEDDING_DIM - vec.size))
    norm = float(np.linalg.norm(vec))
    if norm < 1e-8:
        raise ValueError("无法从音频提取有效声纹特征")
    vec = vec / norm
    return [float(x) for x in vec.tolist()]


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
