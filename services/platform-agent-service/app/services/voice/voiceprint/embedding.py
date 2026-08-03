"""ERes2Net-Large 说话人嵌入（FunASR / ModelScope，512 维）。"""

from __future__ import annotations

import logging
import threading
import wave
from collections.abc import Sequence
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 512
DEFAULT_MODEL_ID = "iic/speech_eres2net_large_sv_zh-cn_3dspeaker_16k"
_TARGET_SR = 16000

_model_lock = threading.Lock()
_sv_model: Any | None = None
_sv_model_id: str | None = None


def current_model_id() -> str:
    from app.config import settings

    configured = (settings.voiceprint_model_id or "").strip()
    return configured or DEFAULT_MODEL_ID


def embedding_dim() -> int:
    from app.config import settings

    dim = int(settings.voiceprint_embedding_dim or EMBEDDING_DIM)
    return dim if dim > 0 else EMBEDDING_DIM


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
    global _sv_model, _sv_model_id
    model_id = current_model_id()
    if _sv_model is not None and _sv_model_id == model_id:
        return _sv_model
    with _model_lock:
        if _sv_model is not None and _sv_model_id == model_id:
            return _sv_model
        from funasr import AutoModel

        device = _resolve_device()
        logger.info("加载 ERes2Net-Large 声纹模型 model_id=%s device=%s", model_id, device)
        loaded = AutoModel(model=model_id, device=device, disable_update=True)
        if loaded is None:
            raise RuntimeError("ERes2Net-Large 声纹模型加载失败")
        _sv_model = loaded
        _sv_model_id = model_id
        return loaded


def reset_sv_model_for_tests() -> None:
    global _sv_model, _sv_model_id
    with _model_lock:
        _sv_model = None
        _sv_model_id = None


def _write_wav(path: Path, samples: np.ndarray, *, sample_rate: int) -> None:
    pcm = np.clip(samples * 32767.0, -32768, 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())


def extract_embedding_from_waveform(
    samples: np.ndarray,
    *,
    sample_rate: int = _TARGET_SR,
) -> list[float]:
    """从 float32 波形提取 L2 归一化嵌入。"""
    if samples.size < int(0.2 * sample_rate):
        raise ValueError("音频过短，无法提取声纹特征")
    energy = float(np.sqrt(np.mean(np.square(samples))))
    if energy < 1e-4:
        raise ValueError("音频能量过低，请靠近麦克风重新录入")

    dim = embedding_dim()
    tmp_path: Path | None = None
    try:
        with NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        _write_wav(tmp_path, samples, sample_rate=sample_rate)
        model = get_sv_model()
        with _model_lock:
            raw = model.generate(input=str(tmp_path))
        if not raw or not isinstance(raw, list) or "spk_embedding" not in raw[0]:
            raise ValueError("无法从音频提取有效声纹特征")
        emb = raw[0]["spk_embedding"]
        if hasattr(emb, "detach"):
            emb = emb.detach().cpu().numpy()
        vec = np.asarray(emb, dtype=np.float64).reshape(-1)
        if vec.size != dim:
            if vec.size > dim:
                vec = vec[:dim]
            else:
                vec = np.pad(vec, (0, dim - vec.size))
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


def aggregate_scores(scores: Sequence[float], *, mode: str = "max") -> float:
    if not scores:
        return 0.0
    if mode == "mean_top_m":
        ordered = sorted((float(s) for s in scores), reverse=True)
        top = ordered[: min(3, len(ordered))]
        return float(sum(top) / len(top))
    return float(max(scores))


def model_loaded() -> bool:
    return _sv_model is not None
