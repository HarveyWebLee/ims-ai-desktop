"""
知识检索 Subagent（P1-3）

官方落点：LangChain Subagents 模式——子任务包成工具，仅将摘要回灌主 agent，
避免长 hits 进入主对话 checkpointer（见 docs.langchain.com multi-agent/subagents）。

本实现：
- 检索：复用 retrieve_knowledge_blocks
- 摘要：优先短模型；失败/关闭则抽取式截断
- 无 checkpointer / 不共享主 thread messages
"""

from __future__ import annotations

import concurrent.futures
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "你是平台知识库检索摘要助手。根据给定检索片段，用简洁中文归纳与用户问题相关的要点。"
    "只依据片段作答，禁止编造；不确定处标明「片段未覆盖」。"
    "输出结构：1）结论要点（条目）2）可选操作提示 3）来源标题列表。"
    "全文控制在 400 字以内。"
)


def _snippet(text: str, max_chars: int) -> str:
    body = re.sub(r"\s+", " ", (text or "").strip())
    if len(body) <= max_chars:
        return body
    return body[: max(0, max_chars - 1)] + "…"


def _sources_from_blocks(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for b in blocks:
        sources.append(
            {
                "title": str(b.get("title") or "").strip(),
                "source": str(b.get("source") or "").strip(),
                "score": b.get("score"),
            }
        )
    return sources


def extractive_summary(
    query: str,
    blocks: list[dict[str, Any]],
    *,
    snippet_chars: int = 220,
    max_total_chars: int = 1400,
) -> str:
    """无 LLM 时的确定性摘要：标题 + 截断正文。"""
    if not blocks:
        return "未检索到相关知识（向量库未配置或无命中）。"
    lines = [f"针对「{query.strip() or '查询'}」的知识要点："]
    for i, b in enumerate(blocks, 1):
        title = str(b.get("title") or "").strip()
        src = str(b.get("source") or "").strip()
        head = f"{i}. {title}".strip() if title else f"{i}."
        if src:
            head = f"{head}（{src}）"
        lines.append(f"{head}\n{_snippet(str(b.get('text') or ''), snippet_chars)}")
    text = "\n\n".join(lines)
    if len(text) > max_total_chars:
        return text[: max_total_chars - 1] + "…"
    return text


def _llm_summarize(query: str, blocks: list[dict[str, Any]]) -> str | None:
    """短模型摘要；失败返回 None（由调用方回退抽取式）。"""
    from app.config import settings
    from app.models.router import resolve_chat_model
    from contracts.context import current_model_id

    if not settings.agent_subagent_knowledge_llm:
        return None

    model_id = (settings.agent_subagent_knowledge_model or "").strip()
    if not model_id:
        # 优先会话当前模型；否则 flash
        model_id = (current_model_id.get() or "").strip() or "qwen3-8b"

    snippet_chars = max(80, int(settings.agent_subagent_knowledge_snippet_chars))
    ref_parts: list[str] = []
    for i, b in enumerate(blocks, 1):
        title = str(b.get("title") or b.get("source") or "").strip()
        head = f"{i}. {title}" if title else f"{i}."
        ref_parts.append(f"{head}\n{_snippet(str(b.get('text') or ''), snippet_chars)}")
    reference = "\n\n".join(ref_parts)

    try:
        model = resolve_chat_model(model_id, streaming=False).bind(
            max_tokens=max(64, int(settings.agent_subagent_knowledge_max_tokens)),
            temperature=0,
        )
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"【用户问题】\n{query.strip()}\n\n【检索片段】\n{reference}\n\n请输出摘要："
                ),
            },
        ]
        timeout = float(settings.agent_subagent_knowledge_timeout_seconds)
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(model.invoke, messages)
            response = future.result(timeout=timeout)
        content = getattr(response, "content", response)
        if isinstance(content, list):
            parts: list[str] = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(str(block.get("text") or ""))
                else:
                    parts.append(str(block))
            text = "".join(parts).strip()
        else:
            text = str(content or "").strip()
        return text or None
    except Exception as exc:  # noqa: BLE001
        logger.warning("knowledge subagent llm summarize failed: %s", exc)
        return None


def research_knowledge(
    query: str,
    *,
    top_k: int | None = None,
) -> dict[str, Any]:
    """
    执行检索子任务并返回摘要载荷（供 ToolMessage / Gateway）。

    返回字段：
      ok, summary, data.hit_count, data.sources, data.mode
    故意不含全文 hits，避免污染主 agent 上下文。
    """
    from app.config import settings
    from app.rag.context import retrieve_knowledge_blocks

    q = (query or "").strip()
    if not q:
        return {
            "ok": True,
            "summary": "查询为空，未执行检索。",
            "data": {"hit_count": 0, "sources": [], "mode": "empty"},
        }

    if not settings.agent_subagent_knowledge_enabled:
        # 关闭时仍检索，但只回抽取式短摘要（兼容旧调用）
        blocks = retrieve_knowledge_blocks(q, top_k=top_k)
        summary = extractive_summary(
            q,
            blocks,
            snippet_chars=max(80, int(settings.agent_rag_passive_snippet_chars)),
        )
        return {
            "ok": True,
            "summary": summary,
            "data": {
                "hit_count": len(blocks),
                "sources": _sources_from_blocks(blocks),
                "mode": "extractive_disabled_flag",
            },
        }

    blocks = retrieve_knowledge_blocks(q, top_k=top_k)
    if not blocks:
        return {
            "ok": True,
            "summary": "未检索到相关知识（向量库未配置或无命中）。",
            "data": {"hit_count": 0, "sources": [], "mode": "empty"},
        }

    llm_text = _llm_summarize(q, blocks)
    if llm_text:
        mode = "llm_summary"
        summary = llm_text
    else:
        mode = "extractive"
        summary = extractive_summary(
            q,
            blocks,
            snippet_chars=max(80, int(settings.agent_subagent_knowledge_snippet_chars)),
        )

    return {
        "ok": True,
        "summary": summary,
        "data": {
            "hit_count": len(blocks),
            "sources": _sources_from_blocks(blocks),
            "mode": mode,
        },
    }
