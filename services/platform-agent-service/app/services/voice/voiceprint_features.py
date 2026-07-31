"""声纹特征：PCM16 频谱嵌入（无重依赖，适合小规模白名单门禁）。"""

from __future__ import annotations

import math
import struct
from collections.abc import Sequence

import numpy as np

# 固定维度，便于入库与比对
EMBEDDING_DIM = 64
_TARGET_SR = 16000


def _pcm16_mono_samples(
    audio_bytes: bytes, *, sample_rate: int | None = None
) -> tuple[np.ndarray, int]:
    """
    解析 PCM16 LE 或带 WAV 头的音频为 float32 mono 波形。
    """
    raw = audio_bytes
    sr = sample_rate or _TARGET_SR
    if len(raw) >= 44 and raw[:4] == b"RIFF" and raw[8:12] == b"WAVE":
        # 简易 WAV：找 data chunk
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
        # 线性重采样到 16k
        duration = len(samples) / float(sample_rate)
        target_len = max(1, int(duration * _TARGET_SR))
        x_old = np.linspace(0.0, 1.0, num=len(samples), endpoint=False)
        x_new = np.linspace(0.0, 1.0, num=target_len, endpoint=False)
        samples = np.interp(x_new, x_old, samples).astype(np.float32)
        sr = _TARGET_SR
    return samples, sr


def extract_embedding(
    audio_bytes: bytes,
    *,
    sample_rate: int | None = None,
) -> list[float]:
    """
    从 PCM/WAV 提取 L2 归一化频谱嵌入。

    说明：面向同麦环境小规模说话人门禁，非商用级生物识别。
    """
    samples, _sr = _pcm16_mono_samples(audio_bytes, sample_rate=sample_rate)
    # 去直流 + 预加重
    samples = samples - float(np.mean(samples))
    if len(samples) > 1:
        samples = np.append(samples[0], samples[1:] - 0.97 * samples[:-1])

    frame = 512
    hop = 256
    if len(samples) < frame:
        samples = np.pad(samples, (0, frame - len(samples)))

    windows: list[np.ndarray] = []
    for start in range(0, len(samples) - frame + 1, hop):
        chunk = samples[start : start + frame] * np.hanning(frame)
        spec = np.abs(np.fft.rfft(chunk))
        # 对数幅度，压缩动态范围
        log_mag = np.log1p(spec)
        # 均匀分箱到 EMBEDDING_DIM
        bins = np.array_split(log_mag, EMBEDDING_DIM)
        vec = np.array([float(np.mean(b)) if len(b) else 0.0 for b in bins], dtype=np.float32)
        windows.append(vec)

    if not windows:
        raise ValueError("无法从音频提取特征")
    stacked = np.stack(windows, axis=0)
    mean = np.mean(stacked, axis=0)
    std = np.std(stacked, axis=0)
    feat = np.concatenate([mean, std]).astype(np.float32)
    # 截断/填充到固定维（mean+std=128 → 压到 64：交替取）
    if feat.size >= EMBEDDING_DIM:
        feat = feat[:EMBEDDING_DIM]
    else:
        feat = np.pad(feat, (0, EMBEDDING_DIM - feat.size))
    norm = float(np.linalg.norm(feat))
    if norm < 1e-8:
        raise ValueError("音频能量过低，请靠近麦克风重新录入")
    feat = feat / norm
    return [float(x) for x in feat.tolist()]


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
    # 维度对齐
    if len(merged) < EMBEDDING_DIM:
        merged.extend([0.0] * (EMBEDDING_DIM - len(merged)))
    merged = merged[:EMBEDDING_DIM]
    norm = math.sqrt(sum(x * x for x in merged)) or 1.0
    return [x / norm for x in merged]
