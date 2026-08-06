"""Qdrant 切块与内存态向量存储单测（不依赖真实 Embedding / Docker）。"""

from __future__ import annotations

from pathlib import Path

import pytest
from qdrant_client import QdrantClient

from app.infrastructure.vector.chunking import chunk_text
from app.infrastructure.vector.store import VectorStoreService


class _FakeEmbeddings:
    """确定性假 Embedding：用字符码填充到固定维度。"""

    def __init__(self, size: int = 8) -> None:
        self.size = size

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vec(text)

    def _vec(self, text: str) -> list[float]:
        if not text:
            return [0.0] * self.size
        seed = sum(ord(c) for c in text) % 97
        return [((seed + i) % 10) / 10.0 for i in range(self.size)]


def test_chunk_text_respects_overlap_and_non_empty() -> None:
    text = "第一段内容。\n" + ("很长的一行文字。" * 40) + "\n结尾。"
    chunks = chunk_text(text, chunk_size=80, chunk_overlap=20)
    assert len(chunks) >= 2
    assert all(c.strip() for c in chunks)


def test_chunk_text_rejects_bad_overlap() -> None:
    with pytest.raises(ValueError):
        chunk_text("abc", chunk_size=10, chunk_overlap=10)


def test_vector_store_upsert_and_search(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "app.infrastructure.vector.store.settings.qdrant_vector_size",
        8,
    )
    monkeypatch.setattr(
        "app.infrastructure.vector.store.settings.qdrant_collection",
        "test_docs",
    )

    client = QdrantClient(":memory:")
    store = VectorStoreService(
        collection="test_docs",
        client=client,
        embeddings=_FakeEmbeddings(size=8),
    )
    store.ensure_collection()
    ids = store.upsert_texts(
        ["告警确认需要值班员在侧栏操作", "BPMN 编排用于多步 Plan"],
        metadatas=[
            {"source": "ops.md", "filename": "ops.md"},
            {"source": "bpmn.md", "filename": "bpmn.md"},
        ],
    )
    assert len(ids) == 2

    hits = store.similarity_search("告警确认", limit=2)
    assert hits
    assert any("告警" in h.text for h in hits)

    doc = tmp_path / "note.md"
    doc.write_text("导出告警报表可使用 download_file 工具。", encoding="utf-8")
    count = store.ingest_file(doc)
    assert count >= 1

    filtered = store.similarity_search("导出", limit=3, source_contains="note.md")
    assert filtered
    assert all("note.md" in str(h.payload.get("source")) for h in filtered)

    context = store.format_context(filtered, max_chars=2000)
    assert "导出" in context or "download_file" in context


def test_upsert_texts_batches_without_losing_chunk_index(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """分批 upsert 时 chunk_index 仍为全局序号，且多批均写入。"""
    monkeypatch.setattr(
        "app.infrastructure.vector.store.settings.qdrant_vector_size",
        8,
    )
    monkeypatch.setattr(
        "app.infrastructure.vector.store.settings.vector_upsert_batch_size",
        3,
    )

    client = QdrantClient(":memory:")
    store = VectorStoreService(
        collection="test_batch",
        client=client,
        embeddings=_FakeEmbeddings(size=8),
    )
    store.ensure_collection()

    texts = [f"片段-{i}-知识内容" for i in range(7)]
    ids = store.upsert_texts(
        texts,
        metadatas=[{"source": "big.md"} for _ in texts],
        source="big.md",
    )
    assert len(ids) == 7
    assert len(set(ids)) == 7

    hits, _ = store.scroll_points(limit=20, source_equals="big.md")
    assert len(hits) == 7
    indices = sorted(int(h.payload.get("chunk_index", -1)) for h in hits)
    assert indices == list(range(7))


def test_ingest_file_replacing_drops_stale_chunks(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """内容变短后先 upsert 再删陈旧点，不残留旧片段。"""
    monkeypatch.setattr(
        "app.infrastructure.vector.store.settings.qdrant_vector_size",
        8,
    )
    monkeypatch.setattr(
        "app.infrastructure.vector.store.settings.vector_chunk_size",
        40,
    )
    monkeypatch.setattr(
        "app.infrastructure.vector.store.settings.vector_chunk_overlap",
        0,
    )
    monkeypatch.setattr(
        "app.infrastructure.vector.store.settings.knowledge_docs_dir",
        str(tmp_path),
    )

    client = QdrantClient(":memory:")
    store = VectorStoreService(
        collection="test_replace",
        client=client,
        embeddings=_FakeEmbeddings(size=8),
    )
    store.ensure_collection()

    doc = tmp_path / "policy.md"
    # 足够长以切出多块
    doc.write_text(("旧规程段落内容。" * 20) + "\n", encoding="utf-8")
    first_chunks, first_deleted = store.ingest_file_replacing(doc)
    assert first_chunks >= 2
    assert first_deleted == 0

    doc.write_text("新短规程。\n", encoding="utf-8")
    second_chunks, second_deleted = store.ingest_file_replacing(doc)
    assert second_chunks >= 1
    assert second_deleted >= 1

    from app.infrastructure.vector.source_keys import normalize_source

    hits, _ = store.scroll_points(limit=50, source_equals=normalize_source(doc))
    assert len(hits) == second_chunks
    assert all("新短规程" in h.text for h in hits)
    assert all(h.payload.get("doc_id") for h in hits)


def test_ingest_file_defaults_to_replace(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """ingest_file 默认可靠替换，避免裸 upsert 残留幽灵 chunk。"""
    monkeypatch.setattr("app.infrastructure.vector.store.settings.qdrant_vector_size", 8)
    monkeypatch.setattr("app.infrastructure.vector.store.settings.vector_chunk_size", 40)
    monkeypatch.setattr("app.infrastructure.vector.store.settings.vector_chunk_overlap", 0)
    monkeypatch.setattr(
        "app.infrastructure.vector.store.settings.knowledge_docs_dir",
        str(tmp_path),
    )

    client = QdrantClient(":memory:")
    store = VectorStoreService(
        collection="test_default_replace",
        client=client,
        embeddings=_FakeEmbeddings(size=8),
    )
    store.ensure_collection()

    doc = tmp_path / "guide.md"
    doc.write_text(("旧指南内容段落。" * 20) + "\n", encoding="utf-8")
    assert store.ingest_file(doc) >= 2

    doc.write_text("新短指南。\n", encoding="utf-8")
    assert store.ingest_file(doc) >= 1

    from app.infrastructure.vector.source_keys import normalize_source

    hits, _ = store.scroll_points(limit=50, source_equals=normalize_source(doc))
    assert all("新短指南" in h.text for h in hits)
    assert not any("旧指南" in h.text for h in hits)


def test_audit_orphans_detects_missing_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("app.infrastructure.vector.store.settings.qdrant_vector_size", 8)
    monkeypatch.setattr(
        "app.infrastructure.vector.store.settings.knowledge_docs_dir",
        str(tmp_path),
    )

    client = QdrantClient(":memory:")
    store = VectorStoreService(
        collection="test_audit",
        client=client,
        embeddings=_FakeEmbeddings(size=8),
    )
    store.ensure_collection()

    doc = tmp_path / "alive.md"
    doc.write_text("仍在磁盘的文档。\n", encoding="utf-8")
    store.ingest_file(doc)

    gone = tmp_path / "gone.md"
    gone.write_text("即将删除的文档。\n", encoding="utf-8")
    store.ingest_file(gone)
    gone.unlink()

    audit = store.audit_orphans(docs_root=tmp_path)
    assert audit["documents"] == 2
    assert audit["orphan_count"] == 1
    assert any("gone.md" in str(o.get("source")) for o in audit["orphans"])


def test_normalize_source_and_doc_id(tmp_path: Path) -> None:
    from app.infrastructure.vector.source_keys import compute_doc_id, normalize_source

    doc = tmp_path / "a" / "b.md"
    doc.parent.mkdir(parents=True)
    doc.write_text("x", encoding="utf-8")
    src = normalize_source(doc)
    assert "\\" not in src
    assert src.endswith("a/b.md")

    doc_id = compute_doc_id(src, docs_root=tmp_path)
    assert doc_id == "a/b.md"
