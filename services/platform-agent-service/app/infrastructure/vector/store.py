"""
Qdrant 向量存储服务：建集合、写入文档片段、语义检索。

典型用法
--------
  from app.infrastructure.vector.store import VectorStoreService

  store = VectorStoreService()
  store.ensure_collection()
  store.upsert_texts(["告警确认流程…"], metadatas=[{"source": "ops.md"}])
  hits = store.similarity_search("如何确认告警", limit=5)
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import settings
from app.infrastructure.vector.chunking import chunk_text
from app.infrastructure.vector.client import get_qdrant_client
from app.infrastructure.vector.embeddings import resolve_embeddings
from app.infrastructure.vector.source_keys import (
    compute_doc_id,
    normalize_source,
    source_lookup_candidates,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SearchHit:
    """单条检索结果。"""

    id: str
    score: float
    text: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class DirectoryIngestResult:
    """目录入库汇总：成功文件与失败列表。"""

    files: dict[str, dict[str, Any]]
    failed: list[dict[str, str]]

    @property
    def chunk_total(self) -> int:
        return sum(int(v.get("chunks") or 0) for v in self.files.values())

    @property
    def deleted_total(self) -> int:
        return sum(int(v.get("deleted") or 0) for v in self.files.values())


def _stable_point_id(collection: str, doc_id: str, chunk_index: int, text: str) -> str:
    """
    由 doc_id + 内容生成稳定 UUID，便于重复入库时覆盖同一片段（幂等 upsert）。
    """
    key = doc_id or "_"
    digest = hashlib.sha256(f"{collection}|{key}|{chunk_index}|{text}".encode()).hexdigest()
    return str(uuid.UUID(digest[:32]))


def _default_docs_root() -> Path | None:
    """与 knowledge API 一致的文档根；解析失败返回 None。"""
    raw = (settings.knowledge_docs_dir or "").strip()
    if raw:
        try:
            return Path(raw).expanduser().resolve()
        except OSError:
            return None
    try:
        service_root = Path(settings.agent_service_root).resolve()
        return (service_root.parent.parent / "prj-docs").resolve()
    except OSError:
        return None


class VectorStoreService:
    """面向业务的 Qdrant 封装（建库 / 入库 / 检索）。"""

    def __init__(
        self,
        *,
        collection: str | None = None,
        client: Any | None = None,
        embeddings: Any | None = None,
    ) -> None:
        self.collection = collection or settings.qdrant_collection
        self._client = client
        self._embeddings = embeddings

    @property
    def client(self):
        if self._client is None:
            self._client = get_qdrant_client()
        return self._client

    @property
    def embeddings(self):
        if self._embeddings is None:
            self._embeddings = resolve_embeddings()
        return self._embeddings

    def ensure_collection(self) -> None:
        """若不存在则按配置维度创建 Cosine 集合。"""
        from qdrant_client.models import Distance, VectorParams

        if self.client.collection_exists(self.collection):
            return
        self.client.create_collection(
            collection_name=self.collection,
            vectors_config=VectorParams(
                size=settings.qdrant_vector_size,
                distance=Distance.COSINE,
            ),
        )
        logger.info(
            "已创建 Qdrant collection=%s size=%s",
            self.collection,
            settings.qdrant_vector_size,
        )

    def upsert_texts(
        self,
        texts: list[str],
        *,
        metadatas: list[dict[str, Any]] | None = None,
        source: str = "",
    ) -> list[str]:
        """
        对文本列表做 embedding 并 upsert 到当前 collection。

        按 ``vector_upsert_batch_size`` 分批 embedding + upsert，避免单次
        HTTP JSON 超过 Qdrant 默认 32MB 限制。

        返回写入的 point id 列表（``chunk_index`` 仍为全文内全局序号）。
        """
        from qdrant_client.models import PointStruct

        if not texts:
            return []
        if metadatas is not None and len(metadatas) != len(texts):
            raise ValueError("metadatas 长度必须与 texts 一致")

        self.ensure_collection()
        batch_size = max(1, int(settings.vector_upsert_batch_size))
        ids: list[str] = []

        for start in range(0, len(texts), batch_size):
            end = min(start + batch_size, len(texts))
            batch_texts = texts[start:end]
            vectors = self.embeddings.embed_documents(batch_texts)
            if len(vectors) != len(batch_texts):
                raise RuntimeError("Embedding 返回数量与输入文本不一致")

            points: list[PointStruct] = []
            for offset, (text, vector) in enumerate(zip(batch_texts, vectors, strict=True)):
                index = start + offset
                meta = dict(metadatas[index]) if metadatas else {}
                src = normalize_source(meta.get("source") or source or "")
                doc_id = str(meta.get("doc_id") or "").strip() or compute_doc_id(
                    src, docs_root=_default_docs_root()
                )
                point_id = _stable_point_id(self.collection, doc_id, index, text)
                payload = {
                    **meta,
                    "source": src,
                    "doc_id": doc_id,
                    "text": text,
                    "chunk_index": index,
                }
                points.append(PointStruct(id=point_id, vector=vector, payload=payload))
                ids.append(point_id)

            self.client.upsert(collection_name=self.collection, points=points, wait=True)

        return ids

    def _prepare_file_chunks(
        self,
        path: Path | str,
        *,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
        encoding: str = "utf-8",
        extra_metadata: dict[str, Any] | None = None,
    ) -> tuple[list[str], list[dict[str, Any]], str]:
        """抽取并切块；返回 (chunks, metadatas, source)。抽取失败不改库。"""
        from app.infrastructure.vector.extractors import (
            IMAGE_SUFFIXES,
            STRUCTURED_SUFFIXES,
            ExtractError,
            extract_text,
        )

        file_path = Path(path)
        if not file_path.is_file():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        try:
            raw = extract_text(file_path, encoding=encoding)
        except ExtractError:
            raise

        chunks = chunk_text(
            raw,
            chunk_size=chunk_size or settings.vector_chunk_size,
            chunk_overlap=chunk_overlap
            if chunk_overlap is not None
            else settings.vector_chunk_overlap,
        )
        # extra_metadata 可覆盖 source（如 replace 保留原路径键）
        if extra_metadata and extra_metadata.get("source"):
            source = normalize_source(extra_metadata["source"])
        else:
            source = normalize_source(file_path)

        if not chunks:
            return [], [], source

        docs_root = _default_docs_root()
        if extra_metadata and str(extra_metadata.get("doc_id") or "").strip():
            doc_id = str(extra_metadata["doc_id"]).strip()
        else:
            doc_id = compute_doc_id(source, docs_root=docs_root)

        rel_parts = file_path.parts
        suffix = file_path.suffix.lower()
        if suffix in IMAGE_SUFFIXES:
            media_kind = "image"
        elif suffix in {".xlsx", ".xls", ".csv", ".tsv"}:
            media_kind = "table"
        elif suffix in STRUCTURED_SUFFIXES:
            media_kind = "document"
        else:
            media_kind = "text"

        base_meta = {
            "source": source,
            "doc_id": doc_id,
            "filename": file_path.name,
            "suffix": suffix,
            "media_kind": media_kind,
            "rel_path": "/".join(rel_parts[-4:]) if len(rel_parts) > 4 else file_path.name,
            **(extra_metadata or {}),
        }
        # 覆盖后再强制规范化，避免 extra_metadata 写回反斜杠
        base_meta["source"] = source
        base_meta["doc_id"] = doc_id

        metadatas = [dict(base_meta) for _ in chunks]
        return chunks, metadatas, source

    def ingest_file(
        self,
        path: Path | str,
        *,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
        encoding: str = "utf-8",
        extra_metadata: dict[str, Any] | None = None,
        replace: bool = True,
    ) -> int:
        """
        读取单个文件（多格式抽取）→ 切块 → 入库。

        默认 ``replace=True``：走可靠替换（先 upsert 再删同 doc_id/source 陈旧点），
        避免内容变更后残留幽灵片段。仅当明确需要追加写时传 ``replace=False``。
        """
        if replace:
            chunks, _deleted = self.ingest_file_replacing(
                path,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                encoding=encoding,
                extra_metadata=extra_metadata,
            )
            return chunks

        chunks, metadatas, source = self._prepare_file_chunks(
            path,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            encoding=encoding,
            extra_metadata=extra_metadata,
        )
        if not chunks:
            return 0
        self.upsert_texts(chunks, metadatas=metadatas, source=source)
        return len(chunks)

    def ingest_file_replacing(
        self,
        path: Path | str,
        *,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
        encoding: str = "utf-8",
        extra_metadata: dict[str, Any] | None = None,
    ) -> tuple[int, int]:
        """
        可靠替换入库：先抽取/upsert（wait=True），再删除同 doc_id（及 source 变体）下未覆盖的旧点。

        抽取失败时不改向量库，避免「先删后写失败」导致知识空洞。
        返回 ``(写入片段数, 删除的陈旧片段数)``。
        """
        chunks, metadatas, source = self._prepare_file_chunks(
            path,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            encoding=encoding,
            extra_metadata=extra_metadata,
        )
        doc_id = ""
        if metadatas:
            doc_id = str(metadatas[0].get("doc_id") or "")
        if not doc_id:
            doc_id = compute_doc_id(source, docs_root=_default_docs_root())

        if not chunks:
            # 空正文仍清理旧点，与「同名替换为空」语义一致
            deleted = self.delete_by_source(source, also_doc_id=True)
            return 0, deleted

        new_ids = set(self.upsert_texts(chunks, metadatas=metadatas, source=source))
        stale_ids = self._collect_stale_ids(new_ids, source=source, doc_id=doc_id)
        deleted = self.delete_by_ids(stale_ids) if stale_ids else 0
        return len(chunks), deleted

    def _collect_stale_ids(
        self,
        new_ids: set[str],
        *,
        source: str,
        doc_id: str,
    ) -> list[str]:
        """收集同文档下未被本次 upsert 覆盖的旧 point id。"""
        stale: list[str] = []
        seen: set[str] = set()

        def _absorb(batch: list[SearchHit]) -> None:
            for hit in batch:
                if hit.id in new_ids or hit.id in seen:
                    continue
                seen.add(hit.id)
                stale.append(hit.id)

        if doc_id:
            offset: Any = None
            while True:
                batch, offset = self.scroll_points(limit=256, offset=offset, doc_id_equals=doc_id)
                _absorb(batch)
                if offset is None:
                    break

        for cand in source_lookup_candidates(source):
            offset = None
            while True:
                batch, offset = self.scroll_points(limit=256, offset=offset, source_equals=cand)
                _absorb(batch)
                if offset is None:
                    break
        return stale

    def ingest_directory(
        self,
        root: Path | str,
        *,
        glob: str = "**/*",
        suffixes: set[str] | None = None,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
        try_unknown: bool = False,
        replace: bool = True,
    ) -> DirectoryIngestResult:
        """
        递归扫描任意层级目录并入库（默认 ``**/*``）。

        默认按文件可靠替换；返回成功明细与失败列表（抽取失败不中断整目录）。
        """
        from app.infrastructure.vector.extractors import (
            DEFAULT_KNOWLEDGE_SUFFIXES,
            UNSUPPORTED_BINARY_SUFFIXES,
            ExtractError,
        )

        directory = Path(root)
        if not directory.is_dir():
            raise NotADirectoryError(f"目录不存在: {directory}")

        allowed = set(suffixes) if suffixes is not None else set(DEFAULT_KNOWLEDGE_SUFFIXES)
        skip_dirs = {
            ".venv",
            "node_modules",
            "__pycache__",
            ".git",
            "dist",
            "build",
            ".idea",
            ".vscode",
            ".cursor",
            "venv",
        }
        files: dict[str, dict[str, Any]] = {}
        failed: list[dict[str, str]] = []
        for file_path in sorted(directory.glob(glob)):
            if not file_path.is_file():
                continue
            parts_lower = {p.lower() for p in file_path.parts}
            if parts_lower & skip_dirs:
                continue

            suffix = file_path.suffix.lower()
            if suffix in UNSUPPORTED_BINARY_SUFFIXES:
                continue
            if suffix not in allowed and not try_unknown:
                continue

            rel = str(file_path.relative_to(directory))
            try:
                if replace:
                    chunks, deleted = self.ingest_file_replacing(
                        file_path,
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap,
                    )
                else:
                    chunks = self.ingest_file(
                        file_path,
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap,
                        replace=False,
                    )
                    deleted = 0
            except (ExtractError, UnicodeDecodeError, OSError, ValueError) as exc:
                logger.warning("跳过文件 %s: %s", file_path, exc)
                failed.append({"path": rel, "error": str(exc)})
                continue
            source = normalize_source(file_path)
            files[rel] = {
                "chunks": chunks,
                "deleted": deleted,
                "source": source,
                "doc_id": compute_doc_id(source, docs_root=_default_docs_root()),
            }
        return DirectoryIngestResult(files=files, failed=failed)

    def similarity_search(
        self,
        query: str,
        *,
        limit: int = 5,
        score_threshold: float | None = None,
        source_contains: str | None = None,
    ) -> list[SearchHit]:
        """语义检索：返回按相似度降序的片段。"""
        if not query.strip():
            return []

        self.ensure_collection()
        vector = self.embeddings.embed_query(query)
        # 多取若干条再本地过滤 source，避免依赖尚未创建的 payload 全文索引
        fetch_limit = limit * 3 if source_contains else limit
        result = self.client.query_points(
            collection_name=self.collection,
            query=vector,
            limit=fetch_limit,
            score_threshold=score_threshold,
            with_payload=True,
        )
        hits: list[SearchHit] = []
        needle = (source_contains or "").lower()
        for point in result.points:
            payload = dict(point.payload or {})
            source = str(payload.get("source") or "")
            if needle and needle not in source.lower():
                continue
            text = str(payload.get("text") or "")
            hits.append(
                SearchHit(
                    id=str(point.id),
                    score=float(point.score or 0.0),
                    text=text,
                    payload=payload,
                )
            )
            if len(hits) >= limit:
                break
        return hits

    def format_context(self, hits: list[SearchHit], *, max_chars: int = 4000) -> str:
        """将检索结果拼成可注入 Prompt 的上下文文本。"""
        parts: list[str] = []
        used = 0
        for i, hit in enumerate(hits, start=1):
            source = hit.payload.get("source") or hit.payload.get("filename") or ""
            block = f"[{i}] (score={hit.score:.4f} source={source})\n{hit.text}"
            if used + len(block) > max_chars and parts:
                break
            parts.append(block)
            used += len(block) + 2
        return "\n\n".join(parts)

    def count(self) -> int:
        """当前 collection 中的点数；集合不存在时返回 0。"""
        if not self.client.collection_exists(self.collection):
            return 0
        info = self.client.get_collection(self.collection)
        return int(info.points_count or 0)

    def scroll_points(
        self,
        *,
        limit: int = 20,
        offset: Any = None,
        source_equals: str | None = None,
        source_contains: str | None = None,
        doc_id_equals: str | None = None,
        with_vectors: bool = False,
    ) -> tuple[list[SearchHit], Any]:
        """
        分页浏览（非语义检索）。

        返回 ``(hits, next_offset)``；``next_offset`` 为 None 表示已到末页。
        """
        from qdrant_client.models import FieldCondition, Filter, MatchText, MatchValue

        if not self.client.collection_exists(self.collection):
            return [], None

        must: list[Any] = []
        if doc_id_equals:
            must.append(FieldCondition(key="doc_id", match=MatchValue(value=doc_id_equals)))
        if source_equals:
            must.append(FieldCondition(key="source", match=MatchValue(value=source_equals)))

        query_filter = Filter(must=must) if must else None
        if source_contains and not must:
            # MatchText 依赖 payload 全文索引；未建索引时回退为拉取后本地过滤
            try:
                query_filter = Filter(
                    must=[
                        FieldCondition(
                            key="source",
                            match=MatchText(text=source_contains),
                        ),
                    ]
                )
            except Exception:  # noqa: BLE001
                query_filter = None

        records, next_offset = self.client.scroll(
            collection_name=self.collection,
            limit=limit,
            offset=offset,
            with_payload=True,
            with_vectors=with_vectors,
            scroll_filter=query_filter,
        )

        needle = (source_contains or "").lower() if source_contains and query_filter is None else ""
        hits: list[SearchHit] = []
        for point in records:
            payload = dict(point.payload or {})
            source = str(payload.get("source") or "")
            if needle and needle not in source.lower():
                continue
            hits.append(
                SearchHit(
                    id=str(point.id),
                    score=0.0,
                    text=str(payload.get("text") or ""),
                    payload=payload,
                )
            )
        return hits, next_offset

    def delete_by_ids(self, ids: list[str]) -> int:
        """按 point id 删除；返回请求删除的数量（集合不存在则为 0）。"""
        from typing import cast

        from qdrant_client.models import ExtendedPointId, PointIdsList

        cleaned = [i for i in ids if i]
        if not cleaned:
            return 0
        if not self.client.collection_exists(self.collection):
            return 0
        self.client.delete(
            collection_name=self.collection,
            points_selector=PointIdsList(points=cast(list[ExtendedPointId], cleaned)),
            wait=True,
        )
        return len(cleaned)

    def _delete_collected_ids(self, ids: list[str]) -> int:
        if not ids:
            return 0
        batch_size = 256
        for i in range(0, len(ids), batch_size):
            self.delete_by_ids(ids[i : i + batch_size])
        return len(ids)

    def delete_by_doc_id(self, doc_id: str) -> int:
        """删除 payload.doc_id 精确等于给定值的全部点。"""
        key = (doc_id or "").strip()
        if not key:
            raise ValueError("doc_id 不能为空")
        if not self.client.collection_exists(self.collection):
            return 0

        ids: list[str] = []
        offset: Any = None
        while True:
            batch, offset = self.scroll_points(limit=256, offset=offset, doc_id_equals=key)
            ids.extend(h.id for h in batch)
            if offset is None:
                break
        deleted = self._delete_collected_ids(ids)
        if deleted:
            logger.info(
                "已按 doc_id 删除 collection=%s doc_id=%s count=%s",
                self.collection,
                key,
                deleted,
            )
        return deleted

    def delete_by_source(self, source: str, *, also_doc_id: bool = True) -> int:
        """
        删除与给定 source 相关的全部点。

        会尝试 source 路径变体；默认同时按推导出的 ``doc_id`` 删除，避免规范化前后残留。
        返回实际删除的点数（去重后）。
        """
        src = (source or "").strip()
        if not src:
            raise ValueError("source 不能为空")
        if not self.client.collection_exists(self.collection):
            return 0

        id_set: set[str] = set()
        for cand in source_lookup_candidates(src):
            offset: Any = None
            while True:
                batch, offset = self.scroll_points(limit=256, offset=offset, source_equals=cand)
                id_set.update(h.id for h in batch)
                if offset is None:
                    break

        if also_doc_id:
            doc_id = compute_doc_id(src, docs_root=_default_docs_root())
            if doc_id:
                offset = None
                while True:
                    batch, offset = self.scroll_points(
                        limit=256, offset=offset, doc_id_equals=doc_id
                    )
                    id_set.update(h.id for h in batch)
                    if offset is None:
                        break

        ids = list(id_set)
        deleted = self._delete_collected_ids(ids)
        if deleted:
            logger.info(
                "已按 source 删除 collection=%s source=%s count=%s",
                self.collection,
                normalize_source(src) or src,
                deleted,
            )
        return deleted

    def replace_file(
        self,
        path: Path | str,
        *,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
        encoding: str = "utf-8",
        extra_metadata: dict[str, Any] | None = None,
    ) -> int:
        """
        更新（整文件可靠替换）：等价于 ``ingest_file_replacing``，返回新写入的 chunk 数。
        """
        chunks, _deleted = self.ingest_file_replacing(
            path,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            encoding=encoding,
            extra_metadata=extra_metadata,
        )
        return chunks

    def list_document_summaries(
        self,
        *,
        max_points: int = 20_000,
    ) -> list[dict[str, Any]]:
        """
        按 source 聚合文档摘要（含 doc_id、chunk_count、磁盘是否存在）。
        """
        by_source: dict[str, dict[str, Any]] = {}
        order: list[str] = []
        offset: Any = None
        scanned = 0
        while scanned < max_points:
            batch_limit = min(256, max_points - scanned)
            hits, offset = self.scroll_points(limit=batch_limit, offset=offset)
            if not hits:
                break
            scanned += len(hits)
            for hit in hits:
                payload = dict(hit.payload or {})
                source = str(payload.get("source") or "").strip()
                if not source:
                    continue
                if source not in by_source:
                    doc_id = str(payload.get("doc_id") or "").strip() or compute_doc_id(
                        source, docs_root=_default_docs_root()
                    )
                    filename = str(payload.get("filename") or "") or Path(source).name
                    file_exists = Path(source).is_file()
                    by_source[source] = {
                        "source": source,
                        "doc_id": doc_id,
                        "filename": filename,
                        "chunk_count": 0,
                        "file_exists": file_exists,
                    }
                    order.append(source)
                by_source[source]["chunk_count"] = int(by_source[source]["chunk_count"]) + 1
            if offset is None:
                break
        return [by_source[key] for key in order]

    def audit_orphans(
        self,
        *,
        docs_root: Path | str | None = None,
        max_points: int = 20_000,
    ) -> dict[str, Any]:
        """
        审计库内文档：磁盘文件缺失的视为孤儿。

        返回 orphan 列表与计数；``docs_root`` 仅写入结果元数据（是否存在以 source 路径为准）。
        """
        root = None
        if docs_root is not None:
            try:
                root = Path(docs_root).expanduser().resolve()
            except OSError:
                root = None
        else:
            root = _default_docs_root()

        summaries = self.list_document_summaries(max_points=max_points)
        orphans = [item for item in summaries if not item.get("file_exists")]
        return {
            "docs_root": str(root) if root else None,
            "documents": len(summaries),
            "orphan_count": len(orphans),
            "orphans": orphans,
            "scanned_documents": len(summaries),
        }

    def drop_collection(self) -> bool:
        """删除整个 collection；不存在返回 False。"""
        if not self.client.collection_exists(self.collection):
            return False
        self.client.delete_collection(self.collection)
        logger.warning("已删除 Qdrant collection=%s", self.collection)
        return True
