"""Stage 4：语义检索纠错（Qdrant，中等成本；尽量不调 LLM）。

优先使用设备/变量实体术语，其次知识库术语——适配「打开某某设备」等下发指令场景。
"""

from __future__ import annotations

import difflib
import logging
import re
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

_CJK_TERM_RE = re.compile(r"[\u4e00-\u9fff]{2,6}")
_ENTITY_CJK_RE = re.compile(r"[\u4e00-\u9fff]{2,20}")
_ENTITY_NAME_RE = re.compile(
    r"(?=.*[\u4e00-\u9fff])[\u4e00-\u9fffA-Za-z0-9][\u4e00-\u9fffA-Za-z0-9.\\-_]{1,23}$"
)
_CODE_RE = re.compile(r"[A-Za-z][\w.\-]{1,31}")
_HAS_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


def _extract_kb_terms(blocks: list[dict[str, Any]]) -> list[str]:
    """
    从知识库检索块抽取可替换术语。
    只取标题与完整 2~6 字 CJK 片段，不再切前后缀子串（避免「查近三天」切出「查近」误伤「查询」）。
    """
    seen: set[str] = set()
    terms: list[str] = []

    def _add(term: str) -> None:
        t = (term or "").strip()
        if len(t) < 2 or len(t) > 6 or t in seen:
            return
        if not (_CJK_TERM_RE.fullmatch(t) or re.fullmatch(r"[A-Za-z][\w-]{1,31}", t)):
            return
        seen.add(t)
        terms.append(t)

    for block in blocks:
        title = str(block.get("title") or "").strip()
        text = str(block.get("text") or "").strip()
        _add(title)
        for blob in (title, text):
            for match in _CJK_TERM_RE.findall(blob):
                _add(match)
    terms.sort(key=len, reverse=True)
    return terms[:40]


def _extract_entity_terms(blocks: list[dict[str, Any]]) -> list[str]:
    """
    从实体检索块抽取设备名/编码、变量名。
    优先用 payload.terms；长度放宽以覆盖真实设备名称。
    """
    seen: set[str] = set()
    terms: list[str] = []

    def _add(term: str) -> None:
        t = (term or "").strip()
        if not t or t in seen:
            return
        # 含中文的设备/变量名（可含数字，如「冷冻水泵1号」）；纯编码；其它中英混合
        if _ENTITY_NAME_RE.fullmatch(t) or _ENTITY_CJK_RE.fullmatch(t):
            pass
        elif _CODE_RE.fullmatch(t):
            if len(t) > 32:
                return
        else:
            if not (2 <= len(t) <= 24):
                return
        seen.add(t)
        terms.append(t)

    for block in blocks:
        for term in block.get("terms") or []:
            _add(str(term))
        _add(str(block.get("title") or ""))
    return _sort_entity_terms(terms)[:48]


def _replace_near_miss(raw: str, term: str, *, min_ratio: float = 0.78) -> str | None:
    """
    等长近错替换（SequenceMatcher）。
    要求足够多的逐字命中，避免同分时错位窗口（如「开冷冻水泵1」抢在「冷冻水泵1好」前）。
    """
    n = len(term)
    if n < 2 or n > 24:
        return None
    # 较长术语提高阈值，降低误替换
    ratio_floor = min_ratio if n <= 4 else max(min_ratio, 0.82)
    # 允许约 1~2 字误差
    min_exact = n - 1 if n <= 8 else n - 2
    best: tuple[float, int, int, int, str] | None = None  # ratio, exact, start, end, term
    for i in range(0, len(raw) - n + 1):
        window = raw[i : i + n]
        if term == window:
            return None
        # 编码忽略大小写比较
        if term.isascii() and window.isascii() and term.lower() == window.lower():
            if term == window:
                return None
            return raw[:i] + term + raw[i + n :]
        exact = sum(
            1 for a, b in zip(term, window, strict=True) if a == b or a.lower() == b.lower()
        )
        if exact < min_exact:
            continue
        ratio = difflib.SequenceMatcher(None, term.lower(), window.lower()).ratio()
        if ratio < ratio_floor:
            continue
        candidate = (ratio, exact, i, i + n, term)
        if best is None or (candidate[1], candidate[0]) > (best[1], best[0]):
            best = candidate
    if best is None:
        return None
    _, _, start, end, replacement = best
    return raw[:start] + replacement + raw[end:]


def _apply_terms(raw: str, terms: list[str]) -> str | None:
    out = raw
    for term in terms:
        if term in out:
            continue
        # 大小写不同的编码已存在则规范化
        if term.isascii():
            lowered = out.lower()
            idx = lowered.find(term.lower())
            if idx >= 0:
                current = out[idx : idx + len(term)]
                if current != term:
                    return out[:idx] + term + out[idx + len(term) :]
                continue
        replaced = _replace_near_miss(out, term)
        if replaced and replaced != out:
            return replaced
    return None


def _sort_entity_terms(terms: list[str]) -> list[str]:
    """含中文的名称优先，再按长度降序（避免短编码抢先误伤）。"""

    def _key(t: str) -> tuple[int, int]:
        has_cjk = 1 if _HAS_CJK_RE.search(t) else 0
        return (-has_cjk, -len(t))

    return sorted(terms, key=_key)


def apply_semantic_correction(text: str, *, context: str = "") -> str | None:
    """
    向量检索后做近错替换；无法确定时返回 None（交给 LLM）。

    检索顺序：实体集合优先，再知识库。
    context 仅拼进检索 query，替换仍只作用于本段 text。
    """
    raw = (text or "").strip()
    if not raw or not (settings.qdrant_url or "").strip():
        return None
    if not settings.transcribe_rag_enabled:
        return None
    try:
        from app.rag.context import retrieve_entity_blocks, retrieve_knowledge_blocks

        top_k = max(1, int(settings.transcribe_rag_top_k))
        threshold = float(settings.transcribe_correct_min_score)
        query = f"{(context or '').strip()} {raw}".strip()

        entity_blocks = retrieve_entity_blocks(
            query,
            top_k=top_k,
            score_threshold=threshold,
        )
        entity_hit = _apply_terms(raw, _extract_entity_terms(entity_blocks))
        if entity_hit:
            return entity_hit

        kb_blocks = retrieve_knowledge_blocks(
            query,
            top_k=top_k,
            score_threshold=threshold,
        )
        if not kb_blocks:
            return None
        return _apply_terms(raw, _extract_kb_terms(kb_blocks))
    except Exception as exc:  # noqa: BLE001
        logger.debug("semantic correction failed: %s", exc)
        return None
