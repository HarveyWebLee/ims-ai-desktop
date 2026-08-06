"""Playbook 匹配、缓存与注入格式化。"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from app.services.playbook.loader import (
    Playbook,
    default_playbooks_dir,
    load_playbooks_from_dir,
)

logger = logging.getLogger(__name__)

_cached: list[Playbook] | None = None
_cached_dir: str | None = None

PLAYBOOK_SECTION_HEADER = "【场景 Playbook（按步骤执行，优先于临场发挥）】"


@dataclass(frozen=True)
class PlaybookMatch:
    """匹配结果（含得分）。"""

    playbook: Playbook
    score: int


def resolve_playbooks_dir() -> Path:
    """当前生效的 Playbook 目录（自定义或内置）。"""
    from app.config import settings

    custom = (settings.agent_playbook_dir or "").strip()
    if custom:
        return Path(custom)
    return default_playbooks_dir()


def _resolve_dir() -> Path:
    return resolve_playbooks_dir()


def clear_playbook_cache() -> None:
    """清空内存缓存（测试 / 热更新）。"""
    global _cached, _cached_dir
    _cached = None
    _cached_dir = None


def reload_playbooks() -> list[Playbook]:
    """强制从磁盘重载，并尝试语义索引同步。"""
    clear_playbook_cache()
    loaded = list_playbooks()
    try:
        from app.services.playbook.semantic import reindex_playbooks

        reindex_playbooks(loaded)
    except Exception:  # noqa: BLE001
        logger.exception("playbook semantic reindex after reload failed")
    return loaded


def list_playbooks() -> list[Playbook]:
    """返回已加载 playbook（带目录级缓存）。"""
    global _cached, _cached_dir
    directory = _resolve_dir()
    key = str(directory.resolve())
    if _cached is not None and _cached_dir == key:
        return list(_cached)
    loaded = load_playbooks_from_dir(directory)
    _cached = loaded
    _cached_dir = key
    logger.debug("playbooks loaded count=%s dir=%s", len(loaded), key)
    return list(loaded)


def _haystack(*texts: str) -> str:
    return "\n".join(t.strip() for t in texts if (t or "").strip()).lower()


def score_playbook(playbook: Playbook, haystack: str) -> int:
    """关键词命中计分；domains 名出现在文本中时弱加权。"""
    if not haystack:
        return 0
    score = 0
    for trigger in playbook.triggers:
        t = trigger.strip().lower()
        if t and t in haystack:
            # 更长触发词权重略高，减少「告警」淹没「导出告警」歧义时的平局
            score += max(1, min(len(t), 8))
    for domain in playbook.domains:
        d = domain.strip().lower()
        if d and d in haystack:
            score += 1
    return score


def _semantic_bonus(similarity: float) -> int:
    """将 Cosine 相似度映射为与关键词同量级的加分（约 1～12）。"""
    if similarity <= 0:
        return 0
    return max(1, min(12, int(round(similarity * 12))))


def match_playbooks(
    message: str,
    *,
    recent_user_messages: list[str] | None = None,
    max_matches: int | None = None,
) -> list[PlaybookMatch]:
    """
    按用户句 + 近期消息匹配 playbook。

    关键词计分 ∪ 语义召回（可关）；仅返回 score>0；同分比 priority，再比 id。
    「怎么导出 / 注意什么」等说明咨询不注入执行类 Playbook（含导出/告警处置）。
    """
    from app.config import settings
    from app.services.chat_intent import is_howto_guidance_message

    if not settings.agent_playbook_enabled:
        return []
    # 说明咨询优先走知识/文字说明，避免 batch-export / alarm-dispose 诱导立刻调工具
    if is_howto_guidance_message(message):
        return []
    limit = (
        max_matches if max_matches is not None else max(1, int(settings.agent_playbook_max_matches))
    )
    haystack = _haystack(message, *(recent_user_messages or [])[-3:])
    catalog = {pb.id: pb for pb in list_playbooks()}
    scores: dict[str, int] = {}

    for pb in catalog.values():
        s = score_playbook(pb, haystack)
        if s > 0:
            scores[pb.id] = s

    # 语义补充：不替代关键词，只并集加分；失败静默
    try:
        from app.services.playbook.semantic import semantic_search_playbook_ids

        for pid, sim in semantic_search_playbook_ids(message, limit=limit + 2):
            if pid not in catalog:
                continue
            bonus = _semantic_bonus(sim)
            scores[pid] = scores.get(pid, 0) + bonus
    except Exception:  # noqa: BLE001
        logger.exception("playbook semantic merge failed")

    scored: list[PlaybookMatch] = [
        PlaybookMatch(playbook=catalog[pid], score=sc)
        for pid, sc in scores.items()
        if sc > 0 and pid in catalog
    ]
    scored.sort(key=lambda m: (-m.score, -m.playbook.priority, m.playbook.id))
    return scored[:limit]


def format_playbook_section(matches: list[PlaybookMatch]) -> str:
    """格式化为可注入 llm_user_message 的段落。"""
    if not matches:
        return ""
    parts = [PLAYBOOK_SECTION_HEADER]
    for i, m in enumerate(matches, 1):
        pb = m.playbook
        parts.append(f"{i}. {pb.title}（id={pb.id}, v={pb.version}）\n{pb.body}".strip())
    return "\n\n".join(parts)
