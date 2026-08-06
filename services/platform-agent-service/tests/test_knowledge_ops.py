"""P1-5：知识运营 API 与实体同步 status。"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api import entity_sync as entity_sync_api
from app.api import knowledge as knowledge_api
from app.sync.entity_sync_status import (
    clear_entity_sync_status,
    get_entity_sync_status,
    remember_entity_sync_result,
)


@pytest.fixture(autouse=True)
def _clear_sync_status():
    clear_entity_sync_status()
    yield
    clear_entity_sync_status()


@pytest.mark.asyncio
async def test_knowledge_stats_requires_auth():
    with patch(
        "app.api.knowledge.get_current_user_id",
        new_callable=AsyncMock,
        side_effect=HTTPException(status_code=401, detail="未授权"),
    ):
        with pytest.raises(HTTPException) as exc:
            await knowledge_api.knowledge_stats(authorization=None)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_knowledge_stats_when_qdrant_unconfigured():
    with (
        patch(
            "app.api.knowledge.get_current_user_id",
            new_callable=AsyncMock,
            return_value="u1",
        ),
        patch("app.infrastructure.vector.client.is_qdrant_configured", return_value=False),
    ):
        resp = await knowledge_api.knowledge_stats(authorization="Bearer x")
    assert resp["code"] == 0
    assert resp["data"]["enabled"] is False
    assert resp["data"]["points"] == 0


@pytest.mark.asyncio
async def test_knowledge_search_returns_items():
    hit = SimpleNamespace(
        id="h1",
        score=0.91,
        text="告警处置步骤",
        payload={"source": "/tmp/a.md", "filename": "a.md", "chunk_index": 0},
    )
    store = MagicMock()
    store.similarity_search.return_value = [hit]

    with (
        patch(
            "app.api.knowledge.get_current_user_id",
            new_callable=AsyncMock,
            return_value="u1",
        ),
        patch("app.api.knowledge._store", return_value=store),
    ):
        body = knowledge_api.KnowledgeSearchBody(query="告警", limit=3)
        resp = await knowledge_api.knowledge_search(body, authorization="Bearer x")

    assert resp["code"] == 0
    assert resp["data"]["query"] == "告警"
    assert len(resp["data"]["items"]) == 1
    assert resp["data"]["items"][0]["source"] == "/tmp/a.md"
    store.similarity_search.assert_called_once_with("告警", limit=3)


@pytest.mark.asyncio
async def test_knowledge_delete_by_source():
    store = MagicMock()
    store.delete_by_source.return_value = 4

    with (
        patch(
            "app.api.knowledge.get_current_user_id",
            new_callable=AsyncMock,
            return_value="u1",
        ),
        patch("app.api.knowledge._store", return_value=store),
    ):
        body = knowledge_api.KnowledgeDeleteBody(source="/tmp/a.md")
        resp = await knowledge_api.knowledge_delete(body, authorization="Bearer x")

    assert resp["code"] == 0
    assert resp["data"]["deleted"] == 4
    store.delete_by_source.assert_called_once_with("/tmp/a.md")


@pytest.mark.asyncio
async def test_knowledge_drop_requires_confirm():
    with patch(
        "app.api.knowledge.get_current_user_id",
        new_callable=AsyncMock,
        return_value="u1",
    ):
        body = knowledge_api.KnowledgeDropBody(confirm=False)
        resp = await knowledge_api.knowledge_drop_collection(body, authorization="Bearer x")
    assert resp["code"] == 40065


@pytest.mark.asyncio
async def test_knowledge_drop_collection_ok():
    store = MagicMock()
    store.collection = "platform_knowledge"
    store.drop_collection.return_value = True

    with (
        patch(
            "app.api.knowledge.get_current_user_id",
            new_callable=AsyncMock,
            return_value="u1",
        ),
        patch("app.api.knowledge._store", return_value=store),
        patch("app.infrastructure.vector.client.is_qdrant_configured", return_value=True),
    ):
        body = knowledge_api.KnowledgeDropBody(confirm=True)
        resp = await knowledge_api.knowledge_drop_collection(body, authorization="Bearer x")

    assert resp["code"] == 0
    assert resp["data"]["dropped"] is True
    assert resp["data"]["collection"] == "platform_knowledge"
    store.drop_collection.assert_called_once()


@pytest.mark.asyncio
async def test_entity_sync_status_empty_then_remembered():
    with patch(
        "app.api.entity_sync.get_current_user_id",
        new_callable=AsyncMock,
        return_value="u1",
    ):
        empty = await entity_sync_api.entity_sync_status(authorization="Bearer x")
    assert empty["code"] == 0
    assert empty["data"]["result"] is None
    assert empty["data"]["in_progress"] is False
    assert empty["data"]["persisted"] is False
    assert empty["data"]["checkpoints"] == []

    remember_entity_sync_result({"ok": True, "skipped": False, "upserted": 3, "message": "ok"})
    snap = get_entity_sync_status()
    assert snap["result"]["upserted"] == 3
    assert snap["at"]
    assert snap["persisted"] is False

    with patch(
        "app.api.entity_sync.get_current_user_id",
        new_callable=AsyncMock,
        return_value="u1",
    ):
        filled = await entity_sync_api.entity_sync_status(authorization="Bearer x")
    assert filled["data"]["result"]["upserted"] == 3


@pytest.mark.asyncio
async def test_trigger_entity_sync_remembers_result():
    fake = {"ok": True, "skipped": False, "upserted": 2, "message": "synced", "tables": []}
    with (
        patch(
            "app.api.entity_sync.get_current_user_id",
            new_callable=AsyncMock,
            return_value="u1",
        ),
        patch("app.api.entity_sync.run_entity_sync", return_value=fake),
    ):
        resp = await entity_sync_api.trigger_entity_sync(
            entity_sync_api.EntitySyncRequest(),
            authorization="Bearer x",
        )
    assert resp["code"] == 0
    status = get_entity_sync_status()
    assert status["result"]["upserted"] == 2


@pytest.mark.asyncio
async def test_knowledge_export_rebuilds_ordered_text():
    hits = [
        SimpleNamespace(
            id="1",
            text="第二段",
            payload={"source": "logical://a.md", "filename": "a.md", "chunk_index": 1},
        ),
        SimpleNamespace(
            id="0",
            text="第一段",
            payload={"source": "logical://a.md", "filename": "a.md", "chunk_index": 0},
        ),
    ]
    store = MagicMock()
    store.scroll_points.side_effect = [(hits, None)]

    with (
        patch(
            "app.api.knowledge.get_current_user_id",
            new_callable=AsyncMock,
            return_value="u1",
        ),
        patch("app.api.knowledge._store", return_value=store),
    ):
        body = knowledge_api.KnowledgeExportBody(source="logical://a.md")
        resp = await knowledge_api.knowledge_export(body, authorization="Bearer x")

    assert resp["code"] == 0
    assert resp["data"]["from"] == "chunks"
    assert resp["data"]["content"] == "第一段\n\n第二段"
    assert resp["data"]["filename"] == "a.md"


@pytest.mark.asyncio
async def test_knowledge_replace_keeps_source(tmp_path, monkeypatch):
    docs = tmp_path / "prj-docs"
    docs.mkdir()
    existing = docs / "doc.md"
    existing.write_text("# old\n", encoding="utf-8")
    monkeypatch.setattr(
        "app.api.knowledge.settings.knowledge_docs_dir",
        str(docs),
    )

    store = MagicMock()
    store.ingest_file_replacing.return_value = (3, 2)
    upload = MagicMock()
    upload.filename = "new.md"
    upload.read = AsyncMock(return_value=b"# updated\n")

    with (
        patch(
            "app.api.knowledge.get_current_user_id",
            new_callable=AsyncMock,
            return_value="u1",
        ),
        patch("app.api.knowledge._store", return_value=store),
    ):
        resp = await knowledge_api.knowledge_replace(
            upload,
            source=str(existing),
            authorization="Bearer x",
        )

    assert resp["code"] == 0
    from app.infrastructure.vector.source_keys import normalize_source

    assert resp["data"]["source"] == normalize_source(existing)
    assert resp["data"]["migrated"] is False
    assert resp["data"]["chunks"] == 3
    assert resp["data"]["deleted_before"] == 2
    assert existing.read_text(encoding="utf-8") == "# updated\n"
    meta = store.ingest_file_replacing.call_args.kwargs["extra_metadata"]
    assert meta["source"] == normalize_source(existing)


@pytest.mark.asyncio
async def test_knowledge_ingest_uses_replacing(tmp_path, monkeypatch):
    docs = tmp_path / "prj-docs"
    docs.mkdir()
    monkeypatch.setattr("app.api.knowledge.settings.knowledge_docs_dir", str(docs))
    monkeypatch.setattr("app.api.knowledge.settings.knowledge_image_max_bytes", 1024)

    store = MagicMock()
    store.ingest_file_replacing.return_value = (4, 1)
    upload = MagicMock()
    upload.filename = "guide.md"
    upload.read = AsyncMock(return_value=b"# guide\n")

    with (
        patch(
            "app.api.knowledge.get_current_user_id",
            new_callable=AsyncMock,
            return_value="u1",
        ),
        patch("app.api.knowledge._store", return_value=store),
    ):
        resp = await knowledge_api.knowledge_ingest(upload, authorization="Bearer x")

    assert resp["code"] == 0
    assert resp["data"]["chunks"] == 4
    assert resp["data"]["deleted_before"] == 1
    assert (docs / "guide.md").is_file()
    store.ingest_file_replacing.assert_called_once()


@pytest.mark.asyncio
async def test_knowledge_ingest_job_queue_flow(tmp_path, monkeypatch):
    docs = tmp_path / "prj-docs"
    docs.mkdir()
    data_dir = tmp_path / "agent-data"
    data_dir.mkdir()
    monkeypatch.setattr("app.api.knowledge.settings.knowledge_docs_dir", str(docs))
    monkeypatch.setattr("app.api.knowledge.settings.knowledge_image_max_bytes", 1024)
    monkeypatch.setattr("app.services.knowledge_ingest_job.settings.agent_data_dir", str(data_dir))

    from app.services.knowledge_ingest_job import get_ingest_job_manager

    mgr = get_ingest_job_manager()
    mgr.clear_for_tests()

    store = MagicMock()
    store.ingest_file_replacing.return_value = (2, 0)

    good = MagicMock()
    good.filename = "a.md"
    good.read = AsyncMock(return_value=b"# a\n")
    dup = MagicMock()
    dup.filename = "a.md"
    dup.read = AsyncMock(return_value=b"# dup\n")

    with (
        patch(
            "app.api.knowledge.get_current_user_id",
            new_callable=AsyncMock,
            return_value="u1",
        ),
        patch("app.api.knowledge._store", return_value=store),
    ):
        created = await knowledge_api.knowledge_ingest_job_create(authorization="Bearer x")
        assert created["code"] == 0
        job_id = created["data"]["job_id"]

        appended = await knowledge_api.knowledge_ingest_job_append(
            job_id,
            [good, dup],
            authorization="Bearer x",
        )
        assert appended["code"] == 0
        assert appended["data"]["total"] == 2

        committed = await knowledge_api.knowledge_ingest_job_commit(
            job_id,
            authorization="Bearer x",
        )
        assert committed["code"] == 0
        assert committed["data"]["status"] == "running"

        # 等待后台任务完成
        task = mgr._tasks.get("u1")
        if task is not None:
            await task

        status = await knowledge_api.knowledge_ingest_job_status(authorization="Bearer x")
        assert status["code"] == 0
        job = status["data"]["job"]
        assert job["status"] == "completed"
        assert job["succeeded"] == 1
        assert job["failed"] == 1
        assert job["chunks_total"] == 2
        assert status["data"]["in_progress"] is False


@pytest.mark.asyncio
async def test_knowledge_ingest_job_append_chunk_limit():
    from app.services.knowledge_ingest_job import APPEND_CHUNK_MAX_FILES, get_ingest_job_manager

    mgr = get_ingest_job_manager()
    mgr.clear_for_tests()

    with patch(
        "app.api.knowledge.get_current_user_id",
        new_callable=AsyncMock,
        return_value="u1",
    ):
        created = await knowledge_api.knowledge_ingest_job_create(authorization="Bearer x")
        job_id = created["data"]["job_id"]
        files = [MagicMock(filename=f"f{i}.md") for i in range(APPEND_CHUNK_MAX_FILES + 1)]
        resp = await knowledge_api.knowledge_ingest_job_append(
            job_id,
            files,
            authorization="Bearer x",
        )
    assert resp["code"] == 40066


@pytest.mark.asyncio
async def test_knowledge_delete_blocked_while_job_running():
    from app.services.knowledge_ingest_job import get_ingest_job_manager

    mgr = get_ingest_job_manager()
    mgr.clear_for_tests()
    job = mgr.create_job("u1")
    # 直接切到 running 模拟锁定
    job.status = "running"
    mgr._persist(job)

    with patch(
        "app.api.knowledge.get_current_user_id",
        new_callable=AsyncMock,
        return_value="u1",
    ):
        resp = await knowledge_api.knowledge_delete(
            knowledge_api.KnowledgeDeleteBody(source="/tmp/a.md"),
            authorization="Bearer x",
        )
    assert resp["code"] == 40961
    mgr.clear_for_tests()


def test_knowledge_docs_dir_defaults_to_prj_docs(monkeypatch):
    monkeypatch.setattr("app.api.knowledge.settings.knowledge_docs_dir", "")
    monkeypatch.setattr(
        "app.api.knowledge.settings.agent_service_root",
        str(Path("e:/WORK/CODE/ims-ai-desktop/services/platform-agent-service")),
    )
    assert knowledge_api.knowledge_docs_dir().name == "prj-docs"


@pytest.mark.asyncio
async def test_knowledge_documents_paginates_by_source():
    hits_page1 = [
        SimpleNamespace(
            id="1",
            text="a1",
            payload={"source": "/a.md", "filename": "a.md", "chunk_index": 0},
        ),
        SimpleNamespace(
            id="2",
            text="a2",
            payload={"source": "/a.md", "filename": "a.md", "chunk_index": 1},
        ),
        SimpleNamespace(
            id="3",
            text="b1",
            payload={"source": "/b.md", "filename": "b.md", "chunk_index": 0},
        ),
    ]
    store = MagicMock()
    store.collection = "platform_knowledge"
    store.scroll_points.return_value = (hits_page1, None)

    with (
        patch(
            "app.api.knowledge.get_current_user_id",
            new_callable=AsyncMock,
            return_value="u1",
        ),
        patch("app.api.knowledge._store", return_value=store),
    ):
        page1 = await knowledge_api.knowledge_documents(
            page=1,
            page_size=1,
            authorization="Bearer x",
        )
        page2 = await knowledge_api.knowledge_documents(
            page=2,
            page_size=1,
            authorization="Bearer x",
        )

    assert page1["code"] == 0
    assert page1["data"]["total"] == 2
    assert page1["data"]["items"][0]["source"] == "/a.md"
    assert page1["data"]["items"][0]["chunk_count"] == 2
    assert page2["data"]["items"][0]["source"] == "/b.md"
