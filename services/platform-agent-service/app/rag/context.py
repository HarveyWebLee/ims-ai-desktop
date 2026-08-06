"""
Qdrant RAG：检索块注入对话上下文。

见 docs/architecture/05-qdrant-rag.md。
"""

from __future__ import annotations

import logging
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


def retrieve_knowledge_blocks(
    query: str,
    *,
    top_k: int | None = None,
    score_threshold: float | None = None,
) -> list[dict[str, Any]]:
    """
    检索知识片段；失败或未配置时返回空列表（不阻断对话）。

    参数:
        query: 检索句
        top_k: 条数；默认 settings.rag_top_k
        score_threshold: 相似度下限，传给 Qdrant；None 表示不设阈值
    """
    q = (query or "").strip()
    if not q or not (settings.qdrant_url or "").strip():
        return []

    limit = top_k if top_k is not None else settings.rag_top_k
    try:
        from app.infrastructure.vector.client import is_qdrant_configured, probe_qdrant
        from app.rag.store import VectorStoreService

        if not is_qdrant_configured():
            return []
        probe = probe_qdrant()
        if not probe.get("ok"):
            logger.debug("qdrant probe failed: %s", probe)
            return []

        store = VectorStoreService()
        hits = store.similarity_search(
            q,
            limit=max(1, limit),
            score_threshold=score_threshold,
        )
        return [
            {
                "text": h.text,
                "score": h.score,
                "source": (h.payload or {}).get("source"),
                "title": (h.payload or {}).get("title"),
            }
            for h in hits
        ]
    except Exception:  # noqa: BLE001
        logger.exception("retrieve_knowledge_blocks failed")
        return []


def retrieve_entity_blocks(
    query: str,
    *,
    top_k: int | None = None,
    score_threshold: float | None = None,
    entity_types: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    检索设备/变量等实体向量；失败或集合未建时返回空列表。

    返回字段：text / score / source / title / entity_type / terms（可纠错术语列表）。
    """
    q = (query or "").strip()
    if not q or not (settings.qdrant_url or "").strip():
        return []

    limit = top_k if top_k is not None else settings.rag_top_k
    try:
        from app.infrastructure.vector.client import is_qdrant_configured, probe_qdrant
        from app.infrastructure.vector.entity_store import EntityVectorStore

        if not is_qdrant_configured():
            return []
        probe = probe_qdrant()
        if not probe.get("ok"):
            logger.debug("qdrant probe failed (entity): %s", probe)
            return []

        store = EntityVectorStore()
        hits = store.similarity_search(
            q,
            limit=max(1, limit),
            score_threshold=score_threshold,
            entity_types=entity_types or ["device", "variable"],
        )
        blocks: list[dict[str, Any]] = []
        for h in hits:
            payload = dict(h.get("payload") or {})
            terms = _entity_terms_from_payload(payload)
            title = (
                str(payload.get("deviceName") or payload.get("device_name") or "").strip()
                or str(payload.get("show_name") or "").strip()
                or str(payload.get("deviceCode") or payload.get("device_code") or "").strip()
                or str(h.get("entity_key") or "").strip()
            )
            blocks.append(
                {
                    "text": str(h.get("text") or ""),
                    "score": float(h.get("score") or 0.0),
                    "source": str(h.get("source") or payload.get("source") or ""),
                    "title": title,
                    "entity_type": str(h.get("entity_type") or ""),
                    "terms": terms,
                    "kind": "entity",
                }
            )
        return blocks
    except Exception:  # noqa: BLE001
        logger.exception("retrieve_entity_blocks failed")
        return []


def _entity_terms_from_payload(payload: dict[str, Any]) -> list[str]:
    """从实体 payload 抽取设备名/编码、变量名等纠错候选。"""
    # 设备同步已改为 camelCase；兼容历史 snake_case 与变量字段
    keys = (
        "deviceName",
        "device_name",
        "deviceCode",
        "device_code",
        "show_name",
        "var_name",
        "commDeviceName",
        "commDeviceCode",
    )
    seen: set[str] = set()
    terms: list[str] = []
    for key in keys:
        value = str(payload.get(key) or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        terms.append(value)
    return terms


def format_rag_section(
    blocks: list[dict[str, Any]],
    *,
    snippet_chars: int | None = None,
) -> str:
    """
    格式化为可注入 LLM 的「参考知识」段落。

    snippet_chars：单条正文上限；None 时读 settings.agent_rag_passive_snippet_chars。
    截断是为避免长检索污染主对话 HumanMessage（P1-3）。
    """
    if not blocks:
        return ""
    from app.config import settings

    limit = (
        snippet_chars
        if snippet_chars is not None
        else max(1, int(settings.agent_rag_passive_snippet_chars))
    )
    lines = ["【参考知识（来自平台知识库，可能不完整，请结合工具结果判断）】"]
    for i, b in enumerate(blocks, 1):
        src = b.get("source") or ""
        title = b.get("title") or ""
        head = f"{i}. {title} ({src})".strip() if (title or src) else f"{i}."
        raw = str(b.get("text") or "").strip()
        if len(raw) > limit:
            raw = raw[: limit - 1] + "…"
        lines.append(f"{head}\n{raw}".strip())
    return "\n\n".join(lines)
