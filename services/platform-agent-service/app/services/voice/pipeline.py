"""
Multi-stage Correction：Rule → Cache → Dictionary → Vector → LLM。

低成本层优先退出；Dictionary / Vector / LLM 成功后写入 Redis Cache。
"""

from __future__ import annotations

import logging
import time

from app.config import settings
from app.services.voice.cache import cache_get, cache_set
from app.services.voice.dictionary import apply_dictionary_correction
from app.services.voice.llm_stage import apply_llm_correction
from app.services.voice.rules import apply_rule_correction
from app.services.voice.semantic import apply_semantic_correction
from app.services.voice.types import CorrectResult

logger = logging.getLogger(__name__)


def multi_stage_correct(raw_text: str) -> CorrectResult:
    """
    对 ASR 原文做多级纠错。

    返回:
        CorrectResult（含最终文本与停留阶段）
    """
    original = (raw_text or "").strip()
    if not original:
        return CorrectResult(text=raw_text or "", stage="empty", changed=False, raw=raw_text or "")

    started = time.perf_counter()
    text = apply_rule_correction(original)
    if text != original:
        # 规则层不写 cache；继续后续阶段（可能再改）
        pass

    cached = cache_get(text)
    if cached:
        logger.info(
            "voice pipeline cache_hit (%.0fms)",
            (time.perf_counter() - started) * 1000,
        )
        return CorrectResult(
            text=cached,
            stage="cache",
            changed=cached != original,
            raw=original,
        )

    if not settings.transcribe_rag_enabled and not settings.transcribe_dictionary_enabled:
        return CorrectResult(
            text=text,
            stage="rule",
            changed=text != original,
            raw=original,
        )

    # Stage 3 Dictionary
    if settings.transcribe_dictionary_enabled:
        dict_out = apply_dictionary_correction(text)
        if dict_out != text:
            cache_set(text, dict_out)
            cache_set(original, dict_out)
            logger.info(
                "voice pipeline dictionary (%.0fms)",
                (time.perf_counter() - started) * 1000,
            )
            return CorrectResult(
                text=dict_out,
                stage="dictionary",
                changed=True,
                raw=original,
            )

    # Stage 4 Semantic (Vector)
    if settings.transcribe_rag_enabled:
        semantic_out = apply_semantic_correction(text)
        if semantic_out and semantic_out != text:
            cache_set(text, semantic_out)
            cache_set(original, semantic_out)
            logger.info(
                "voice pipeline semantic (%.0fms)",
                (time.perf_counter() - started) * 1000,
            )
            return CorrectResult(
                text=semantic_out,
                stage="semantic",
                changed=True,
                raw=original,
            )

        # Stage 5 LLM（仅必要时）
        llm_out = apply_llm_correction(text)
        if llm_out and llm_out != text:
            cache_set(text, llm_out)
            cache_set(original, llm_out)
            logger.info(
                "voice pipeline llm (%.0fms)",
                (time.perf_counter() - started) * 1000,
            )
            return CorrectResult(
                text=llm_out,
                stage="llm",
                changed=True,
                raw=original,
            )

    logger.info(
        "voice pipeline passthrough stage=rule_or_none (%.0fms)",
        (time.perf_counter() - started) * 1000,
    )
    return CorrectResult(
        text=text,
        stage="rule",
        changed=text != original,
        raw=original,
    )
