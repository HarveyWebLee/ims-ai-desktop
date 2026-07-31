"""
语音转写后纠错入口（兼容旧调用方）。

实现已收敛到 ``app.services.voice.pipeline.multi_stage_correct``：
Rule → Redis Cache → Dictionary → Vector → LLM。
"""

from __future__ import annotations

from app.services.voice.pipeline import multi_stage_correct


def correct_asr_transcript(raw_text: str) -> str:
    """对 ASR 原文做多级纠错；失败/未改动时返回安全文本。"""
    return multi_stage_correct(raw_text).text
