"""Windows 友好原子写：replace 占用时重试并回退直写。"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from app.utils.atomic_write import atomic_write_bytes, atomic_write_text


def test_atomic_write_text_happy(tmp_path: Path) -> None:
    target = tmp_path / "job.json"
    atomic_write_text(target, '{"ok": true}')
    assert target.read_text(encoding="utf-8") == '{"ok": true}'
    assert not list(tmp_path.glob(".*.tmp"))


def test_atomic_write_text_retries_permission_error(tmp_path: Path) -> None:
    target = tmp_path / "job.json"
    target.write_text("old", encoding="utf-8")
    calls = {"n": 0}
    real_replace = __import__("os").replace

    def flaky_replace(src: str | Path, dst: str | Path) -> None:
        calls["n"] += 1
        if calls["n"] < 3:
            err = PermissionError(5, "拒绝访问")
            err.winerror = 5  # type: ignore[attr-defined]
            raise err
        real_replace(src, dst)

    with patch("app.utils.atomic_write.os.replace", side_effect=flaky_replace):
        with patch("app.utils.atomic_write.time.sleep"):
            atomic_write_text(target, "new", retries=5, base_delay_s=0.01)

    assert target.read_text(encoding="utf-8") == "new"
    assert calls["n"] == 3


def test_atomic_write_text_fallback_direct_write(tmp_path: Path) -> None:
    target = tmp_path / "job.json"
    target.write_text("old", encoding="utf-8")

    def always_busy(_src: str | Path, _dst: str | Path) -> None:
        err = PermissionError(5, "拒绝访问")
        err.winerror = 5  # type: ignore[attr-defined]
        raise err

    with patch("app.utils.atomic_write.os.replace", side_effect=always_busy):
        with patch("app.utils.atomic_write.time.sleep"):
            atomic_write_text(target, "fallback", retries=2, base_delay_s=0.01)

    assert target.read_text(encoding="utf-8") == "fallback"


def test_atomic_write_bytes(tmp_path: Path) -> None:
    target = tmp_path / "blob.bin"
    atomic_write_bytes(target, b"\x00\x01\x02")
    assert target.read_bytes() == b"\x00\x01\x02"


def test_ingest_job_persist_does_not_raise_on_disk_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.services import knowledge_ingest_job as mod

    monkeypatch.setattr(mod.settings, "agent_data_dir", str(tmp_path))
    mgr = mod.KnowledgeIngestJobManager()
    job = mgr.create_job("u-win")

    with patch(
        "app.services.knowledge_ingest_job.atomic_write_text", side_effect=OSError("locked")
    ):
        mgr._persist(job)  # 不得抛出，避免拖垮入库主循环

    assert mgr.get_job("u-win") is job
