"""
文档规程批量入库任务队列（按用户）。

流程：create(receiving) → append files → commit(running) → 逐文件可靠入库 → completed。
进度写入进程内存 + JSON 快照，离开设置页后仍可轮询回显。
同一用户同时仅允许一个未结束任务。
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from app.config import settings
from app.utils.atomic_write import atomic_write_text

logger = logging.getLogger(__name__)

JobStatus = Literal["receiving", "running", "completed", "interrupted"]
ItemStatus = Literal["pending", "running", "ok", "error", "skipped"]

_ACTIVE_STATUSES = frozenset({"receiving", "running"})
# 单次 HTTP 追加文件数上限（避免超大 multipart）；总任务文件数不限
APPEND_CHUNK_MAX_FILES = 30


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _jobs_dir() -> Path:
    root = Path(settings.agent_data_dir).expanduser().resolve()
    path = root / "knowledge_ingest_jobs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _snapshot_path(user_id: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in (user_id or "anon"))[:120]
    return _jobs_dir() / f"{safe or 'anon'}.json"


@dataclass
class IngestJobItem:
    filename: str
    path: str
    status: ItemStatus = "pending"
    source: str | None = None
    chunks: int = 0
    deleted_before: int = 0
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "filename": self.filename,
            "path": self.path,
            "status": self.status,
            "source": self.source,
            "chunks": self.chunks,
            "deleted_before": self.deleted_before,
            "error": self.error,
            "ok": self.status == "ok",
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> IngestJobItem:
        status = str(raw.get("status") or "pending")
        if status not in {"pending", "running", "ok", "error", "skipped"}:
            status = "pending"
        return cls(
            filename=str(raw.get("filename") or ""),
            path=str(raw.get("path") or ""),
            status=status,  # type: ignore[arg-type]
            source=(str(raw["source"]) if raw.get("source") else None),
            chunks=int(raw.get("chunks") or 0),
            deleted_before=int(raw.get("deleted_before") or 0),
            error=(str(raw["error"]) if raw.get("error") else None),
        )


@dataclass
class IngestJob:
    job_id: str
    user_id: str
    status: JobStatus
    created_at: str
    updated_at: str
    items: list[IngestJobItem] = field(default_factory=list)
    current_filename: str | None = None
    message: str = ""
    seen_names: set[str] = field(default_factory=set)

    @property
    def total(self) -> int:
        return len(self.items)

    @property
    def done(self) -> int:
        return sum(1 for it in self.items if it.status in {"ok", "error", "skipped"})

    @property
    def succeeded(self) -> int:
        return sum(1 for it in self.items if it.status == "ok")

    @property
    def failed(self) -> int:
        return sum(1 for it in self.items if it.status in {"error", "skipped"})

    @property
    def chunks_total(self) -> int:
        return sum(it.chunks for it in self.items if it.status == "ok")

    @property
    def deleted_total(self) -> int:
        return sum(it.deleted_before for it in self.items if it.status == "ok")

    @property
    def in_progress(self) -> bool:
        return self.status == "running"

    @property
    def percent(self) -> int:
        if self.total <= 0:
            return 0 if self.status != "completed" else 100
        return min(100, int(round(100.0 * self.done / self.total)))

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "user_id": self.user_id,
            "status": self.status,
            "in_progress": self.in_progress,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "total": self.total,
            "done": self.done,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "chunks_total": self.chunks_total,
            "deleted_total": self.deleted_total,
            "percent": self.percent,
            "current_filename": self.current_filename,
            "message": self.message,
            "items": [it.to_dict() for it in self.items],
        }

    def to_snapshot(self) -> dict[str, Any]:
        data = self.to_public_dict()
        data["seen_names"] = sorted(self.seen_names)
        return data

    @classmethod
    def from_snapshot(cls, raw: dict[str, Any]) -> IngestJob:
        status = str(raw.get("status") or "completed")
        if status not in {"receiving", "running", "completed", "interrupted"}:
            status = "completed"
        items = [
            IngestJobItem.from_dict(it) for it in (raw.get("items") or []) if isinstance(it, dict)
        ]
        seen = {str(n) for n in (raw.get("seen_names") or [])}
        if not seen:
            seen = {it.filename for it in items if it.filename}
        return cls(
            job_id=str(raw.get("job_id") or ""),
            user_id=str(raw.get("user_id") or ""),
            status=status,  # type: ignore[arg-type]
            created_at=str(raw.get("created_at") or _utc_now()),
            updated_at=str(raw.get("updated_at") or _utc_now()),
            items=items,
            current_filename=(
                str(raw["current_filename"]) if raw.get("current_filename") else None
            ),
            message=str(raw.get("message") or ""),
            seen_names=seen,
        )


class KnowledgeIngestJobManager:
    """进程内按 user_id 维护最近任务；落盘便于重启后回显。"""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._jobs: dict[str, IngestJob] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}

    def _persist(self, job: IngestJob) -> None:
        """落盘快照；Windows 下文件占用时不得拖垮整批入库。"""
        path = _snapshot_path(job.user_id)
        payload = json.dumps(job.to_snapshot(), ensure_ascii=False, indent=2)
        try:
            atomic_write_text(path, payload)
        except OSError as exc:
            # 内存仍为运行期权威；仅影响重启后回显
            logger.error(
                "入库任务快照落盘失败 user=%s job=%s err=%s",
                job.user_id,
                job.job_id,
                exc,
            )

    def _load_from_disk(self, user_id: str) -> IngestJob | None:
        path = _snapshot_path(user_id)
        if not path.is_file():
            return None
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                return None
            job = IngestJob.from_snapshot(raw)
            if not job.job_id:
                return None
            # 进程重启后无法继续后台任务
            if job.status in _ACTIVE_STATUSES:
                job.status = "interrupted"
                job.current_filename = None
                job.message = "服务重启，入库任务已中断；请重新上传未完成的文件"
                job.updated_at = _utc_now()
                for it in job.items:
                    if it.status in {"pending", "running"}:
                        it.status = "error"
                        it.error = it.error or "任务中断"
                self._persist(job)
            return job
        except Exception as exc:  # noqa: BLE001
            logger.warning("加载入库任务快照失败 user=%s err=%s", user_id, exc)
            return None

    def get_job(self, user_id: str) -> IngestJob | None:
        with self._lock:
            job = self._jobs.get(user_id)
            if job is None:
                job = self._load_from_disk(user_id)
                if job is not None:
                    self._jobs[user_id] = job
            return job

    def is_busy(self, user_id: str) -> bool:
        """仅 running 锁定写操作；receiving 可被新任务覆盖。"""
        job = self.get_job(user_id)
        return bool(job and job.status == "running")

    def create_job(self, user_id: str) -> IngestJob:
        with self._lock:
            existing = self.get_job(user_id)
            if existing and existing.status == "running":
                raise RuntimeError("已有入库任务进行中，请等待完成后再试")
            if existing and existing.status == "receiving":
                # 未提交的接收中任务可被新选择覆盖，避免永久锁死
                existing.status = "interrupted"
                existing.current_filename = None
                existing.message = "已被新的上传任务取代"
                existing.updated_at = _utc_now()
                for it in existing.items:
                    if it.status in {"pending", "running"}:
                        it.status = "error"
                        it.error = it.error or "任务已取消"
                self._persist(existing)
            now = _utc_now()
            job = IngestJob(
                job_id=str(uuid.uuid4()),
                user_id=user_id,
                status="receiving",
                created_at=now,
                updated_at=now,
                message="正在接收上传文件…",
            )
            self._jobs[user_id] = job
            self._persist(job)
            return job

    def append_saved_files(
        self,
        user_id: str,
        job_id: str,
        entries: list[tuple[str, Path]],
    ) -> IngestJob:
        """追加已落盘文件；(filename, path)。同任务重复文件名记 skipped。"""
        with self._lock:
            job = self._require_job(user_id, job_id)
            if job.status != "receiving":
                raise RuntimeError("任务已开始处理，无法继续追加文件")
            for filename, path in entries:
                safe = filename.strip() or path.name
                if safe in job.seen_names:
                    job.items.append(
                        IngestJobItem(
                            filename=safe,
                            path=str(path.resolve()),
                            status="skipped",
                            error="同任务重复文件名，已跳过",
                        )
                    )
                    continue
                job.seen_names.add(safe)
                job.items.append(
                    IngestJobItem(
                        filename=safe,
                        path=str(path.resolve()),
                        status="pending",
                    )
                )
            job.updated_at = _utc_now()
            job.message = f"已接收 {job.total} 个文件，等待提交处理…"
            self._persist(job)
            return job

    def append_save_errors(
        self,
        user_id: str,
        job_id: str,
        errors: list[tuple[str, str]],
    ) -> IngestJob:
        """记录落盘失败的文件（计入 failed，不再入库）。"""
        with self._lock:
            job = self._require_job(user_id, job_id)
            if job.status != "receiving":
                raise RuntimeError("任务已开始处理，无法继续追加文件")
            for filename, error in errors:
                safe = filename.strip() or "upload.bin"
                job.items.append(
                    IngestJobItem(
                        filename=safe,
                        path="",
                        status="error",
                        error=error,
                    )
                )
                job.seen_names.add(safe)
            job.updated_at = _utc_now()
            self._persist(job)
            return job

    def commit(self, user_id: str, job_id: str) -> IngestJob:
        with self._lock:
            job = self._require_job(user_id, job_id)
            if job.status != "receiving":
                raise RuntimeError("任务状态不允许提交")
            if job.total <= 0:
                raise RuntimeError("任务中没有任何文件")
            job.status = "running"
            job.updated_at = _utc_now()
            job.message = "正在入库…"
            self._persist(job)
            return job

    def _require_job(self, user_id: str, job_id: str) -> IngestJob:
        job = self.get_job(user_id)
        if job is None or job.job_id != job_id:
            raise LookupError("入库任务不存在或已过期")
        return job

    def _update_item(self, user_id: str, index: int, **kwargs: Any) -> None:
        with self._lock:
            job = self._jobs.get(user_id)
            if job is None or index < 0 or index >= len(job.items):
                return
            item = job.items[index]
            for key, value in kwargs.items():
                setattr(item, key, value)
            job.updated_at = _utc_now()
            if item.status == "running":
                job.current_filename = item.filename
            job.message = (
                f"正在处理 {job.done + (1 if item.status == 'running' else 0)}/{job.total}"
                f"：{job.current_filename or ''}"
            )
            self._persist(job)

    def _finalize(self, user_id: str, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(user_id)
            if job is None or job.job_id != job_id:
                return
            job.status = "completed"
            job.current_filename = None
            job.updated_at = _utc_now()
            job.message = (
                f"入库完成：成功 {job.succeeded}，失败 {job.failed}，共 {job.chunks_total} 个片段"
            )
            self._persist(job)

    async def run_job(self, user_id: str, job_id: str) -> None:
        from app.api.knowledge import _ingest_saved_path, _store

        try:
            store = _store()
            with self._lock:
                job = self._jobs.get(user_id)
                if job is None or job.job_id != job_id:
                    return
                items = list(job.items)

            for index, item in enumerate(items):
                if item.status != "pending":
                    continue
                self._update_item(user_id, index, status="running", error=None)
                path = Path(item.path)
                try:
                    if not path.is_file():
                        raise FileNotFoundError(f"文件不存在: {path}")
                    data = await asyncio.to_thread(_ingest_saved_path, store, path)
                    self._update_item(
                        user_id,
                        index,
                        status="ok",
                        source=str(data.get("source") or path.resolve()),
                        chunks=int(data.get("chunks") or 0),
                        deleted_before=int(data.get("deleted_before") or 0),
                        error=None,
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.exception("入库任务单项失败 job=%s file=%s", job_id, item.filename)
                    self._update_item(
                        user_id,
                        index,
                        status="error",
                        error=str(exc),
                    )
            self._finalize(user_id, job_id)
        except Exception as exc:  # noqa: BLE001
            logger.exception("入库任务异常中止 job=%s", job_id)
            with self._lock:
                job = self._jobs.get(user_id)
                if job and job.job_id == job_id:
                    job.status = "interrupted"
                    job.current_filename = None
                    job.message = f"入库任务异常中止: {exc}"
                    job.updated_at = _utc_now()
                    for it in job.items:
                        if it.status in {"pending", "running"}:
                            it.status = "error"
                            it.error = it.error or str(exc)
                    self._persist(job)
        finally:
            with self._lock:
                self._tasks.pop(user_id, None)

    def start_background(self, user_id: str, job_id: str) -> None:
        with self._lock:
            existing = self._tasks.get(user_id)
            if existing and not existing.done():
                raise RuntimeError("入库任务已在运行")
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError as exc:
                raise RuntimeError("无事件循环，无法启动入库任务") from exc
            task = loop.create_task(self.run_job(user_id, job_id))
            self._tasks[user_id] = task

    def clear_for_tests(self) -> None:
        with self._lock:
            self._jobs.clear()
            self._tasks.clear()


_MANAGER = KnowledgeIngestJobManager()


def get_ingest_job_manager() -> KnowledgeIngestJobManager:
    return _MANAGER
