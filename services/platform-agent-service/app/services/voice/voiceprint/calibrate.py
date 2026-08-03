"""分数校准：Logistic（+ 可选 S-Norm）。"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_calib: dict[str, Any] | None = None


def _load_calibration() -> dict[str, Any]:
    global _calib
    if _calib is not None:
        return _calib
    from app.config import settings

    path = (settings.voiceprint_calibration_path or "").strip()
    if not path:
        # Cosine 常见同人约 0.5~0.9；默认映射使 ~0.65 → ~0.83
        _calib = {"a": 12.0, "b": -7.8, "snorm": False}
        return _calib
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("calibration json 必须为对象")
        _calib = {
            "a": float(data.get("a", 12.0)),
            "b": float(data.get("b", -7.8)),
            "snorm": bool(data.get("snorm", False)),
            "cohort_mean": float(data.get("cohort_mean", 0.0)),
            "cohort_std": float(data.get("cohort_std", 1.0)),
        }
        return _calib
    except Exception:  # noqa: BLE001
        logger.warning("读取声纹校准文件失败，使用默认 Logistic", exc_info=True)
        _calib = {"a": 12.0, "b": -7.8, "snorm": False}
        return _calib


def reset_calibration_for_tests() -> None:
    global _calib
    _calib = None


def _sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def calibrate_score(score_raw: float) -> float:
    """将 Cosine 原始分映射到近似可信度 [0,1]。"""
    cfg = _load_calibration()
    x = float(score_raw)
    if cfg.get("snorm"):
        std = float(cfg.get("cohort_std") or 1.0)
        if abs(std) < 1e-8:
            std = 1.0
        x = (x - float(cfg.get("cohort_mean") or 0.0)) / std
    a = float(cfg.get("a", 12.0))
    b = float(cfg.get("b", -7.8))
    return float(_sigmoid(a * x + b))
