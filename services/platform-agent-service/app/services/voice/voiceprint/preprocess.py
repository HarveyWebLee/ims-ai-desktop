"""声纹音频预处理：重采样 / 去直流 / 高通 / 响度归一 / VAD / DeepFilterNet3。

VAD 默认走 FunASR fsmn-vad（ModelScope，与声纹模型同源，国内可下）。
仅当本机已有 Silero torch.hub 缓存时才优先用 Silero；禁止运行时访问 GitHub。
"""

from __future__ import annotations

import logging
import struct
import threading
import wave
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

import numpy as np

from app.services.voice.voiceprint.types import PreprocessResult

logger = logging.getLogger(__name__)

_TARGET_SR = 16000
_FUNASR_VAD_MODEL = "fsmn-vad"
_vad_lock = threading.Lock()
_vad_model: Any | None = None
_vad_backend: str | None = None  # silero | funasr
_vad_failed = False
_df_lock = threading.Lock()
_df_model: Any | None = None
_df_state: Any | None = None
_df_failed = False


class PreprocessError(ValueError):
    """预处理失败（短音频 / 能量低 / 管线错误）。"""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _pcm16_mono_samples(
    audio_bytes: bytes, *, sample_rate: int | None = None
) -> tuple[np.ndarray, int]:
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
                    raise PreprocessError("pipeline_failed", "仅支持 16bit 单声道 WAV/PCM")
            elif chunk_id == b"data":
                data = payload
                break
        if not data:
            raise PreprocessError("pipeline_failed", "WAV 中未找到 data 块")
        raw = data
    if len(raw) < 3200:
        raise PreprocessError("audio_too_short", "音频过短，请至少录制 1 秒以上")
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
    return samples, int(sr) if sr > 0 else _TARGET_SR


def _remove_dc(samples: np.ndarray) -> np.ndarray:
    return (samples - float(np.mean(samples))).astype(np.float32)


def _highpass_80hz(samples: np.ndarray, *, sr: int = _TARGET_SR) -> np.ndarray:
    """一阶高通近似 80Hz（无额外依赖）。"""
    rc = 1.0 / (2.0 * np.pi * 80.0)
    dt = 1.0 / float(sr)
    alpha = rc / (rc + dt)
    out = np.empty_like(samples)
    prev_y = 0.0
    prev_x = float(samples[0]) if samples.size else 0.0
    for i, x in enumerate(samples):
        y = alpha * (prev_y + float(x) - prev_x)
        out[i] = y
        prev_y = y
        prev_x = float(x)
    return out.astype(np.float32)


def _loudness_normalize(samples: np.ndarray, *, target_rms: float = 0.1) -> np.ndarray:
    rms = float(np.sqrt(np.mean(np.square(samples))))
    if rms < 1e-8:
        raise PreprocessError("audio_energy_low", "音频能量过低，请靠近麦克风重新录入")
    gain = target_rms / rms
    out = samples * gain
    peak = float(np.max(np.abs(out))) if out.size else 0.0
    if peak > 0.99:
        out = out * (0.99 / peak)
    return out.astype(np.float32)


def _resolve_device() -> str:
    import torch

    from app.config import settings

    configured = (settings.voiceprint_device or "").strip().lower()
    if configured in {"cpu", "cuda"}:
        if configured == "cuda" and not torch.cuda.is_available():
            return "cpu"
        return configured
    return "cuda" if torch.cuda.is_available() else "cpu"


def _try_load_silero_local() -> Any | None:
    """仅使用已存在的 torch.hub 本地缓存，绝不访问 GitHub。"""
    try:
        import torch
    except Exception:  # noqa: BLE001
        return None

    hub_dir = Path(torch.hub.get_dir())
    local_candidates = [
        hub_dir / "snakers4_silero-vad_master",
        hub_dir / "snakers4_silero-vad" / "master",
    ]
    for local_dir in local_candidates:
        if not (local_dir / "hubconf.py").is_file():
            continue
        try:
            model, _utils = torch.hub.load(  # type: ignore[no-untyped-call]
                repo_or_dir=str(local_dir),
                model="silero_vad",
                source="local",
                onnx=False,
            )
            model.eval()
            logger.info("Silero VAD 已从本地缓存加载 path=%s", local_dir)
            return model
        except Exception as exc:  # noqa: BLE001
            logger.debug("本地 Silero 缓存不可用 path=%s err=%s", local_dir, exc)
    return None


def _try_load_funasr_vad() -> Any | None:
    """FunASR fsmn-vad（ModelScope），与 ERes2Net 同源下载通道。"""
    try:
        from funasr import AutoModel

        device = _resolve_device()
        model = AutoModel(model=_FUNASR_VAD_MODEL, device=device, disable_update=True)
        logger.info("FunASR VAD 已加载 model=%s device=%s", _FUNASR_VAD_MODEL, device)
        return model
    except Exception as exc:  # noqa: BLE001
        logger.warning("FunASR VAD 加载失败：%s", exc)
        return None


def _get_vad_model() -> tuple[Any, str] | None:
    global _vad_model, _vad_backend, _vad_failed
    if _vad_failed:
        return None
    if _vad_model is not None and _vad_backend is not None:
        return _vad_model, _vad_backend
    with _vad_lock:
        if _vad_failed:
            return None
        if _vad_model is not None and _vad_backend is not None:
            return _vad_model, _vad_backend

        silero = _try_load_silero_local()
        if silero is not None:
            _vad_model = silero
            _vad_backend = "silero"
            return _vad_model, _vad_backend

        funasr = _try_load_funasr_vad()
        if funasr is not None:
            _vad_model = funasr
            _vad_backend = "funasr"
            return _vad_model, _vad_backend

        _vad_failed = True
        logger.warning("VAD 模型均不可用，本进程内改用能量门限")
        return None


def _energy_vad_mask(samples: np.ndarray, *, frame: int = 512) -> np.ndarray:
    if samples.size < frame:
        return np.ones(samples.size, dtype=bool)
    energies = []
    for i in range(0, samples.size - frame + 1, frame):
        chunk = samples[i : i + frame]
        energies.append(float(np.sqrt(np.mean(np.square(chunk)))))
    if not energies:
        return np.ones(samples.size, dtype=bool)
    thr = max(0.01, float(np.median(energies)) * 0.5)
    mask = np.zeros(samples.size, dtype=bool)
    for idx, e in enumerate(energies):
        if e >= thr:
            start = idx * frame
            mask[start : start + frame] = True
    if not mask.any():
        mask[:] = True
    return mask


def _silero_vad_mask(samples: np.ndarray, model: Any) -> np.ndarray:
    import torch

    window = 512
    speech = np.zeros(samples.size, dtype=bool)
    tensor = torch.from_numpy(samples)
    for start in range(0, max(0, samples.size - window + 1), window):
        chunk = tensor[start : start + window]
        if chunk.numel() < window:
            break
        with torch.no_grad():
            prob = float(model(chunk, _TARGET_SR).item())
        if prob >= 0.5:
            speech[start : start + window] = True
    if not speech.any():
        return _energy_vad_mask(samples)
    return speech


def _write_temp_wav(samples: np.ndarray) -> Path:
    pcm = np.clip(samples * 32767.0, -32768, 32767).astype(np.int16)
    with NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        path = Path(tmp.name)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(_TARGET_SR)
        wf.writeframes(pcm.tobytes())
    return path


def _funasr_vad_mask(samples: np.ndarray, model: Any) -> np.ndarray:
    """FunASR 返回 [[start_ms, end_ms], ...]，据此切有效语音。"""
    tmp_path: Path | None = None
    try:
        tmp_path = _write_temp_wav(samples)
        with _vad_lock:
            raw = model.generate(input=str(tmp_path))
        segments: list[list[float]] = []
        if raw and isinstance(raw, list) and isinstance(raw[0], dict):
            value = raw[0].get("value")
            if isinstance(value, list):
                segments = [list(seg) for seg in value if isinstance(seg, (list, tuple))]
        if not segments:
            return _energy_vad_mask(samples)
        mask = np.zeros(samples.size, dtype=bool)
        for seg in segments:
            if len(seg) < 2:
                continue
            start = max(0, int(float(seg[0]) / 1000.0 * _TARGET_SR))
            end = min(samples.size, int(float(seg[1]) / 1000.0 * _TARGET_SR))
            if end > start:
                mask[start:end] = True
        if not mask.any():
            return _energy_vad_mask(samples)
        return mask
    except Exception as exc:  # noqa: BLE001
        logger.warning("FunASR VAD 推理失败，回退能量门限：%s", exc)
        return _energy_vad_mask(samples)
    finally:
        if tmp_path is not None:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                logger.debug("清理 VAD 临时 WAV 失败 path=%s", tmp_path, exc_info=True)


def _apply_vad(samples: np.ndarray, *, enabled: bool) -> tuple[np.ndarray, int]:
    if not enabled:
        speech_ms = int(round(samples.size / _TARGET_SR * 1000))
        return samples, speech_ms
    loaded = _get_vad_model()
    if loaded is None:
        mask = _energy_vad_mask(samples)
    else:
        model, backend = loaded
        if backend == "silero":
            mask = _silero_vad_mask(samples, model)
        else:
            mask = _funasr_vad_mask(samples, model)
    voiced = samples[mask]
    if voiced.size < int(0.2 * _TARGET_SR):
        raise PreprocessError("audio_too_short", "有效语音过短，请连续说话后再试")
    speech_ms = int(round(voiced.size / _TARGET_SR * 1000))
    return voiced.astype(np.float32), speech_ms


def _get_deepfilternet() -> tuple[Any, Any] | None:
    global _df_model, _df_state, _df_failed
    if _df_failed:
        return None
    if _df_model is not None and _df_state is not None:
        return _df_model, _df_state
    with _df_lock:
        if _df_failed:
            return None
        if _df_model is not None and _df_state is not None:
            return _df_model, _df_state
        try:
            from df.enhance import init_df  # type: ignore[import-not-found]

            model, df_state, _ = init_df()
            _df_model = model
            _df_state = df_state
            logger.info("DeepFilterNet 已加载")
            return _df_model, _df_state
        except Exception:  # noqa: BLE001
            _df_failed = True
            logger.warning(
                "DeepFilterNet 不可用（未安装或加载失败），降噪阶段将跳过",
                exc_info=True,
            )
            return None


def _apply_denoise(samples: np.ndarray, *, enabled: bool) -> np.ndarray:
    if not enabled:
        return samples
    loaded = _get_deepfilternet()
    if loaded is None:
        return samples
    model, df_state = loaded
    try:
        import torch
        from df.enhance import enhance  # type: ignore[import-not-found]

        audio = torch.from_numpy(samples).unsqueeze(0)
        enhanced = enhance(model, df_state, audio)
        out = enhanced.detach().cpu().numpy().reshape(-1).astype(np.float32)
        if out.size == 0:
            raise PreprocessError("pipeline_failed", "降噪输出为空")
        return out
    except PreprocessError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise PreprocessError("pipeline_failed", f"降噪失败: {exc}") from exc


def preprocess_audio(
    audio_bytes: bytes,
    *,
    sample_rate: int | None = None,
    min_speech_ms: int,
    vad_enabled: bool | None = None,
    denoise_enabled: bool | None = None,
) -> PreprocessResult:
    """
    统一预处理管线。

    min_speech_ms: 有效语音下限（录入 / 核验不同）。
    """
    from app.config import settings

    use_vad = settings.voiceprint_vad_enabled if vad_enabled is None else vad_enabled
    use_denoise = (
        settings.voiceprint_denoise_enabled if denoise_enabled is None else denoise_enabled
    )

    samples, sr = _pcm16_mono_samples(audio_bytes, sample_rate=sample_rate)
    if sr != _TARGET_SR:
        duration = len(samples) / float(sr)
        target_len = max(1, int(duration * _TARGET_SR))
        x_old = np.linspace(0.0, 1.0, num=len(samples), endpoint=False)
        x_new = np.linspace(0.0, 1.0, num=target_len, endpoint=False)
        samples = np.interp(x_new, x_old, samples).astype(np.float32)
        sr = _TARGET_SR

    samples = _remove_dc(samples)
    samples = _highpass_80hz(samples, sr=sr)
    samples = _loudness_normalize(samples)
    samples, speech_ms = _apply_vad(samples, enabled=use_vad)
    if speech_ms < min_speech_ms:
        raise PreprocessError(
            "audio_too_short",
            f"有效语音不足 {min_speech_ms}ms（当前 {speech_ms}ms）",
        )
    samples = _apply_denoise(samples, enabled=use_denoise)
    return PreprocessResult(samples=samples, speech_ms=speech_ms, sample_rate=_TARGET_SR)
