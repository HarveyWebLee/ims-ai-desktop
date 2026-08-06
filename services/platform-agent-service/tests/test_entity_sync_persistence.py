"""实体同步水位线与状态持久化（内存路径；无 Postgres）。"""

from __future__ import annotations

from app.sync.entity_sync_status import (
    clear_entity_sync_status,
    get_entity_sync_status,
    remember_entity_sync_result,
    table_to_stream_name,
    upsert_entity_sync_checkpoint,
)


def setup_function() -> None:
    clear_entity_sync_status()


def teardown_function() -> None:
    clear_entity_sync_status()


def test_table_to_stream_name() -> None:
    assert table_to_stream_name("p_device") == "device"
    assert table_to_stream_name("P_DEVICE_VARIABLE") == "variable"
    assert table_to_stream_name("other_tbl") == "other_tbl"


def test_remember_and_checkpoint_in_memory() -> None:
    remember_entity_sync_result({"ok": True, "skipped": False, "upserted": 5, "message": "ok"})
    upsert_entity_sync_checkpoint(
        "device",
        watermark_ts="2026-08-06T01:00:00Z",
        watermark_id="42",
        last_ok=True,
        last_rows_read=5,
        last_upserted=5,
    )
    snap = get_entity_sync_status()
    assert snap["result"]["upserted"] == 5
    assert snap["persisted"] is False
    assert len(snap["checkpoints"]) == 1
    assert snap["checkpoints"][0]["stream_name"] == "device"
    assert snap["checkpoints"][0]["last_ok"] is True
    assert snap["checkpoints"][0]["watermark_id"] == "42"
