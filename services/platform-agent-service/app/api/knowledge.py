"""
文档知识运营 API（P1-5）。

面向设置页：统计 / 浏览 / 试检索 / 上传入库 / 按 source 删除 / 导出 / 按 source 更新。
不暴露 drop_collection。同名文件再传会先删旧 source 再写入。
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Any

from fastapi import Form, UploadFile
from pydantic import BaseModel, Field

from app.api.response import fail, ok
from app.config import settings
from app.middleware.auth import get_current_user_id

_SAFE_NAME_RE = re.compile(r"[^\w.\-()\u4e00-\u9fff]+", re.UNICODE)
_TEXT_EXPORT_SUFFIXES = {".md", ".txt", ".markdown", ".rst", ".csv", ".tsv", ".html", ".htm"}


def knowledge_docs_dir() -> Path:
    """
    文档落盘根目录。

    默认：``<仓根>/prj-docs``（与 ``bash scripts/kb.sh --dir .../prj-docs`` 一致）。
    可用 ``KNOWLEDGE_DOCS_DIR`` 覆盖。
    """
    raw = (settings.knowledge_docs_dir or "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    service_root = Path(settings.agent_service_root).resolve()
    return (service_root.parent.parent / "prj-docs").resolve()


def _safe_filename(name: str) -> str:
    base = Path(name or "upload.bin").name
    cleaned = _SAFE_NAME_RE.sub("_", base).strip("._") or "upload.bin"
    return cleaned[:180]


def _path_under_docs(path: Path, docs: Path) -> bool:
    try:
        path.resolve().relative_to(docs.resolve())
        return True
    except OSError, ValueError:
        return False


def _resolve_save_path(filename: str, *, replace_source: str | None = None) -> Path:
    """新上传落到 prj-docs；更新时尽量写回原 source 同路径（若在文档目录内）。"""
    docs = knowledge_docs_dir()
    docs.mkdir(parents=True, exist_ok=True)
    safe = _safe_filename(filename)
    if replace_source:
        src = Path(replace_source.strip())
        if _path_under_docs(src, docs):
            src.parent.mkdir(parents=True, exist_ok=True)
            return src
        # 旧版 knowledge_uploads 或其他路径：按文件名迁入文档目录
        name = src.name if src.name else safe
        return docs / _safe_filename(name)
    return docs / safe


def _upload_target(filename: str, *, replace_source: str | None = None) -> Path:
    return _resolve_save_path(filename, replace_source=replace_source)


class KnowledgeSearchBody(BaseModel):
    query: str = Field(..., min_length=1)
    limit: int = Field(default=5, ge=1, le=20)


class KnowledgeDeleteBody(BaseModel):
    source: str = Field(..., min_length=1, description="payload.source 精确匹配")


class KnowledgeExportBody(BaseModel):
    source: str = Field(..., min_length=1, description="payload.source 精确匹配")


def _hit_to_dict(hit: Any, *, preview_chars: int = 160) -> dict[str, Any]:
    payload = dict(getattr(hit, "payload", None) or {})
    text = str(getattr(hit, "text", None) or payload.get("text") or "")
    preview = text if len(text) <= preview_chars else text[: preview_chars - 1] + "…"
    return {
        "id": str(getattr(hit, "id", "")),
        "score": float(getattr(hit, "score", 0.0) or 0.0),
        "text_preview": preview,
        "source": str(payload.get("source") or ""),
        "filename": str(payload.get("filename") or ""),
        "chunk_index": payload.get("chunk_index"),
        "media_kind": payload.get("media_kind"),
    }


def _store():
    from app.infrastructure.vector.store import VectorStoreService

    return VectorStoreService()


def _export_filename(source: str, filename: str) -> str:
    name = (filename or Path(source).name or "knowledge.md").strip()
    suffix = Path(name).suffix.lower()
    if suffix not in _TEXT_EXPORT_SUFFIXES:
        stem = Path(name).stem or "knowledge"
        name = f"{stem}.md"
    return _safe_filename(name)


def _collect_source_hits(store: Any, source: str) -> list[Any]:
    hits: list[Any] = []
    offset: Any = None
    while True:
        batch, offset = store.scroll_points(limit=256, offset=offset, source_equals=source)
        hits.extend(batch)
        if offset is None:
            break
    return hits


def _rebuild_text_from_hits(hits: list[Any]) -> tuple[str, str]:
    """按 chunk_index 拼接；返回 (text, filename)。"""
    if not hits:
        raise ValueError("该来源下无知识片段")

    def _chunk_key(hit: Any) -> int:
        payload = dict(getattr(hit, "payload", None) or {})
        raw = payload.get("chunk_index")
        try:
            return int(raw) if raw is not None else 0
        except TypeError, ValueError:
            return 0

    ordered = sorted(hits, key=_chunk_key)
    parts: list[str] = []
    for hit in ordered:
        payload = dict(getattr(hit, "payload", None) or {})
        text = str(getattr(hit, "text", None) or payload.get("text") or "").strip()
        if text:
            parts.append(text)
    if not parts:
        raise ValueError("该来源下无可用正文")
    filename = ""
    for hit in ordered:
        payload = dict(getattr(hit, "payload", None) or {})
        filename = str(payload.get("filename") or "")
        if filename:
            break
    return "\n\n".join(parts), filename


def _export_document(source: str) -> dict[str, Any]:
    """优先读磁盘原文；否则从向量片段重建为可下载文本。"""
    src = source.strip()
    path = Path(src)
    if path.is_file() and path.suffix.lower() in _TEXT_EXPORT_SUFFIXES:
        raw = path.read_text(encoding="utf-8", errors="replace")
        return {
            "source": src,
            "filename": _export_filename(src, path.name),
            "content": raw,
            "from": "file",
        }

    store = _store()
    hits = _collect_source_hits(store, src)
    text, filename = _rebuild_text_from_hits(hits)
    return {
        "source": src,
        "filename": _export_filename(src, filename),
        "content": text,
        "from": "chunks",
        "chunks": len(hits),
    }


async def knowledge_stats(authorization: str | None = None) -> dict[str, Any]:
    await get_current_user_id(authorization)
    try:
        from app.infrastructure.vector.client import is_qdrant_configured, probe_qdrant

        if not is_qdrant_configured():
            return ok(
                {
                    "enabled": False,
                    "ok": False,
                    "collection": settings.qdrant_collection,
                    "points": 0,
                    "message": "未配置 QDRANT_URL",
                }
            )
        probe = await asyncio.to_thread(probe_qdrant)
        store = _store()
        points = await asyncio.to_thread(store.count)
        return ok(
            {
                "enabled": True,
                "ok": bool(probe.get("ok")),
                "collection": settings.qdrant_collection,
                "points": points,
                "probe": probe,
                "upload_dir": str(knowledge_docs_dir()),
                "docs_dir": str(knowledge_docs_dir()),
            }
        )
    except Exception as exc:  # noqa: BLE001
        return fail(50061, f"知识库统计失败: {exc}")


async def knowledge_list(
    *,
    limit: int = 20,
    source_contains: str | None = None,
    authorization: str | None = None,
) -> dict[str, Any]:
    await get_current_user_id(authorization)
    limit = max(1, min(100, int(limit)))
    try:
        store = _store()

        def _run() -> dict[str, Any]:
            hits, next_offset = store.scroll_points(
                limit=limit,
                source_contains=(source_contains or "").strip() or None,
            )
            return {
                "items": [_hit_to_dict(h) for h in hits],
                "next_offset": str(next_offset) if next_offset is not None else None,
                "collection": store.collection,
            }

        data = await asyncio.to_thread(_run)
        return ok(data)
    except Exception as exc:  # noqa: BLE001
        return fail(50062, f"知识浏览失败: {exc}")


_DOC_LIST_MAX_SCAN = 20_000


def _list_documents_page(
    store: Any,
    *,
    page: int,
    page_size: int,
    source_contains: str | None,
) -> dict[str, Any]:
    """
    按 payload.source 聚合为文档后做页码分页。

    扫描点数上限 _DOC_LIST_MAX_SCAN；超限时 truncated=true，total 为已扫到的文档数。
    """
    page = max(1, int(page))
    page_size = max(1, min(100, int(page_size)))
    needle = (source_contains or "").strip() or None

    by_source: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    offset: Any = None
    scanned = 0

    while scanned < _DOC_LIST_MAX_SCAN:
        batch_limit = min(256, _DOC_LIST_MAX_SCAN - scanned)
        hits, offset = store.scroll_points(
            limit=batch_limit,
            offset=offset,
            source_contains=needle,
        )
        if not hits:
            offset = None
            break
        scanned += len(hits)
        for hit in hits:
            payload = dict(getattr(hit, "payload", None) or {})
            source = str(payload.get("source") or "").strip()
            if not source:
                continue
            if source not in by_source:
                filename = str(payload.get("filename") or "") or Path(source).name
                by_source[source] = {
                    "source": source,
                    "filename": filename,
                    "chunk_count": 0,
                }
                order.append(source)
            by_source[source]["chunk_count"] = int(by_source[source]["chunk_count"]) + 1
        if offset is None:
            break

    total = len(order)
    start = (page - 1) * page_size
    end = start + page_size
    items = [by_source[key] for key in order[start:end]]
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "scanned_points": scanned,
        "truncated": offset is not None,
        "collection": store.collection,
    }


async def knowledge_documents(
    *,
    page: int = 1,
    page_size: int = 20,
    source_contains: str | None = None,
    authorization: str | None = None,
) -> dict[str, Any]:
    """文档级分页列表（按 source 去重）。"""
    await get_current_user_id(authorization)
    try:
        store = _store()
        data = await asyncio.to_thread(
            _list_documents_page,
            store,
            page=page,
            page_size=page_size,
            source_contains=source_contains,
        )
        return ok(data)
    except Exception as exc:  # noqa: BLE001
        return fail(50069, f"文档列表失败: {exc}")


async def knowledge_search(
    body: KnowledgeSearchBody,
    authorization: str | None = None,
) -> dict[str, Any]:
    await get_current_user_id(authorization)
    try:
        store = _store()

        def _run() -> dict[str, Any]:
            hits = store.similarity_search(body.query.strip(), limit=body.limit)
            return {
                "query": body.query.strip(),
                "items": [_hit_to_dict(h, preview_chars=220) for h in hits],
            }

        data = await asyncio.to_thread(_run)
        return ok(data)
    except Exception as exc:  # noqa: BLE001
        return fail(50063, f"知识检索失败: {exc}")


async def _save_upload(
    file: UploadFile,
    *,
    replace_source: str | None = None,
) -> Path:
    target = _upload_target(file.filename or "upload.bin", replace_source=replace_source)
    content = await file.read()
    if not content:
        raise ValueError("上传文件为空")
    max_bytes = max(1, int(settings.knowledge_image_max_bytes)) * 4
    if len(content) > max_bytes:
        raise ValueError(f"文件过大（>{max_bytes} 字节）")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return target


async def knowledge_ingest(
    file: UploadFile,
    authorization: str | None = None,
) -> dict[str, Any]:
    """multipart 上传到文档目录（默认 prj-docs）并入库；同名先删旧 source 再写入。"""
    await get_current_user_id(authorization)
    try:
        path = await _save_upload(file)
    except ValueError as exc:
        return fail(40061, str(exc))
    except Exception as exc:  # noqa: BLE001
        return fail(50064, f"保存上传失败: {exc}")

    try:
        store = _store()

        def _run() -> dict[str, Any]:
            source = str(path.resolve())
            deleted = store.delete_by_source(source)
            chunks = store.ingest_file(path)
            return {
                "source": source,
                "filename": path.name,
                "chunks": chunks,
                "deleted_before": deleted,
                "docs_dir": str(knowledge_docs_dir()),
            }

        data = await asyncio.to_thread(_run)
        return ok(data, message=f"已入库 {data['chunks']} 个片段")
    except Exception as exc:  # noqa: BLE001
        return fail(50065, f"入库失败: {exc}")


async def knowledge_replace(
    file: UploadFile,
    source: str = Form(..., min_length=1),
    authorization: str | None = None,
) -> dict[str, Any]:
    """
    按已有 source 更新。

    - source 已在文档目录内：写回原路径并保持 source 键
    - 否则：迁入文档目录，删除旧 source，以新绝对路径入库（与 prj-docs 对齐）
    """
    await get_current_user_id(authorization)
    src = (source or "").strip()
    if not src:
        return fail(40063, "source 不能为空")
    try:
        path = await _save_upload(file, replace_source=src)
    except ValueError as exc:
        return fail(40061, str(exc))
    except Exception as exc:  # noqa: BLE001
        return fail(50064, f"保存上传失败: {exc}")

    try:
        store = _store()
        docs = knowledge_docs_dir()
        keep_source = _path_under_docs(Path(src), docs)
        keep_name = Path(src).name or path.name

        def _run() -> dict[str, Any]:
            deleted = store.delete_by_source(src)
            if keep_source:
                chunks = store.ingest_file(
                    path,
                    extra_metadata={
                        "source": src,
                        "filename": keep_name,
                    },
                )
                return {
                    "source": src,
                    "filename": keep_name,
                    "chunks": chunks,
                    "deleted_before": deleted,
                    "migrated": False,
                    "docs_dir": str(docs),
                }
            # 从 knowledge_uploads 等路径迁入 prj-docs
            if src != str(path.resolve()):
                # 若新路径已有旧片段也清掉，避免双份
                deleted += store.delete_by_source(str(path.resolve()))
            chunks = store.ingest_file(path)
            return {
                "source": str(path.resolve()),
                "filename": path.name,
                "chunks": chunks,
                "deleted_before": deleted,
                "migrated": True,
                "migrated_from": src,
                "docs_dir": str(docs),
            }

        data = await asyncio.to_thread(_run)
        msg = f"已更新 {data['chunks']} 个片段"
        if data.get("migrated"):
            msg += "（已迁入文档目录）"
        return ok(data, message=msg)
    except Exception as exc:  # noqa: BLE001
        return fail(50067, f"更新失败: {exc}")


async def knowledge_export(
    body: KnowledgeExportBody,
    authorization: str | None = None,
) -> dict[str, Any]:
    """导出文档正文（优先磁盘原文，否则拼接片段），供前端触发本地下载。"""
    await get_current_user_id(authorization)
    src = body.source.strip()
    if not src:
        return fail(40064, "source 不能为空")
    try:
        data = await asyncio.to_thread(_export_document, src)
        return ok(data)
    except ValueError as exc:
        return fail(40064, str(exc))
    except Exception as exc:  # noqa: BLE001
        return fail(50068, f"导出失败: {exc}")


async def knowledge_delete(
    body: KnowledgeDeleteBody,
    authorization: str | None = None,
) -> dict[str, Any]:
    await get_current_user_id(authorization)
    src = body.source.strip()
    if not src:
        return fail(40062, "source 不能为空")
    try:
        store = _store()
        deleted = await asyncio.to_thread(store.delete_by_source, src)
        return ok({"source": src, "deleted": deleted}, message=f"已删除 {deleted} 个片段")
    except ValueError as exc:
        return fail(40062, str(exc))
    except Exception as exc:  # noqa: BLE001
        return fail(50066, f"删除失败: {exc}")
