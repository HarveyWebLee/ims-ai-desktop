"""Stage 5：LLM 纠错（高成本，最后一层）。"""

from __future__ import annotations

import concurrent.futures
import logging
import re
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"
_FENCE_RE = re.compile(r"^```(?:\w+)?\s*([\s\S]*?)\s*```$", re.MULTILINE)


@lru_cache(maxsize=1)
def _load_prompt() -> str:
    return (_PROMPTS_DIR / "asr_correct.md").read_text(encoding="utf-8")


def _message_content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("text"):
                parts.append(str(block["text"]))
            elif hasattr(block, "get") and block.get("type") == "text":
                parts.append(str(block.get("text") or ""))
        return "".join(parts).strip()
    return str(content or "").strip()


def _sanitize(raw: str, corrected: str) -> str:
    text = (corrected or "").strip()
    if not text:
        return raw
    fenced = _FENCE_RE.match(text)
    if fenced:
        text = fenced.group(1).strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'「」":
        text = text[1:-1].strip()
    if not text:
        return raw
    if len(text) > max(80, int(len(raw) * 2.5)):
        return raw
    return text


def apply_llm_correction(text: str, *, reference_hint: str = "") -> str | None:
    """调用轻量 LLM；失败返回 None。"""
    raw = (text or "").strip()
    if not raw or not settings.transcribe_rag_enabled:
        return None
    started = time.perf_counter()
    try:
        from app.models.router import resolve_chat_model
        from app.rag.context import retrieve_entity_blocks, retrieve_knowledge_blocks

        top_k = max(1, int(settings.transcribe_rag_top_k))
        threshold = float(settings.transcribe_correct_min_score)
        query = f"{(reference_hint or '').strip()} {raw}".strip()
        # 实体优先：下发指令场景优先注入设备名/编码
        entity_blocks = retrieve_entity_blocks(
            query,
            top_k=top_k,
            score_threshold=threshold,
        )
        kb_blocks = retrieve_knowledge_blocks(
            query,
            top_k=top_k,
            score_threshold=threshold,
        )
        ref_parts: list[str] = []
        if reference_hint:
            ref_parts.append(f"【上文】{reference_hint.strip()}")
        max_chars = max(40, int(settings.transcribe_correct_snippet_chars))
        idx = 1
        for block in entity_blocks[:3]:
            title = str(block.get("title") or "").strip()
            terms = [str(t).strip() for t in (block.get("terms") or []) if str(t).strip()]
            body = " / ".join(terms) if terms else (str(block.get("text") or "").strip() or title)
            if not body:
                continue
            snippet = body if len(body) <= max_chars else body[:max_chars] + "…"
            head = f"{idx}. [实体] {title}".strip() if title else f"{idx}. [实体]"
            ref_parts.append(f"{head}\n{snippet}")
            idx += 1
        for block in kb_blocks[:3]:
            title = str(block.get("title") or "").strip()
            body = str(block.get("text") or "").strip() or title
            if not body:
                continue
            snippet = body if len(body) <= max_chars else body[:max_chars] + "…"
            head = f"{idx}. {title}".strip() if title else f"{idx}."
            ref_parts.append(f"{head}\n{snippet}")
            idx += 1
        reference = "\n\n".join(ref_parts) if ref_parts else "（无）"

        model_id = (settings.transcribe_correct_model or "").strip() or "qwen3.5-flash-2026-02-23"
        model = resolve_chat_model(model_id, streaming=False).bind(
            max_tokens=int(settings.transcribe_correct_max_tokens),
            temperature=0,
        )
        messages = [
            {"role": "system", "content": _load_prompt()},
            {
                "role": "user",
                "content": (
                    f"【ASR 原文】\n{raw}\n\n【参考术语】\n{reference}\n\n只输出纠正后的一行文本："
                ),
            },
        ]
        timeout = float(settings.transcribe_correct_timeout_seconds)
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(model.invoke, messages)
            response = future.result(timeout=timeout)
        out = _sanitize(raw, _message_content_to_text(getattr(response, "content", response)))
        logger.info(
            "voice llm_stage done changed=%s (%.0fms)",
            out != raw,
            (time.perf_counter() - started) * 1000,
        )
        return out if out != raw else None
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "voice llm_stage failed (%.0fms): %s",
            (time.perf_counter() - started) * 1000,
            exc,
        )
        return None
