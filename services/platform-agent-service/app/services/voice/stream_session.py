"""
Streaming ASR 会话 + Pipeline Parallelism。

每个 chunk 提交到线程池独立执行：ASR(累计缓冲) → multi_stage_correct，
不阻塞后续 chunk 提交；完成结果按 seq 覆盖，finish 取最高 seq 或最终全量 ASR。
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

from app.config import settings
from app.services.voice.pipeline import multi_stage_correct

logger = logging.getLogger(__name__)


@dataclass
class ChunkOutcome:
    seq: int
    text: str
    stage: str
    raw_asr: str
    elapsed_ms: float


@dataclass
class StreamSession:
    session_id: str
    model_id: str | None = None
    mime: str = "audio/webm"
    buffer: bytearray = field(default_factory=bytearray)
    lock: threading.RLock = field(default_factory=threading.RLock)
    outcomes: dict[int, ChunkOutcome] = field(default_factory=dict)
    futures: dict[int, Future] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    executor: ThreadPoolExecutor | None = None

    def submit_chunk(
        self,
        *,
        seq: int,
        audio_bytes: bytes,
        mime: str | None = None,
    ) -> dict[str, Any]:
        """
        追加音频并并行提交 ASR+纠错任务；立即返回（不串行等待）。
        """
        if seq < 0:
            raise ValueError("seq 必须 >= 0")
        with self.lock:
            if mime:
                self.mime = mime
            self.buffer.extend(audio_bytes)
            snapshot = bytes(self.buffer)
            content_type = self.mime
            model_id = self.model_id
            if self.executor is None:
                workers = max(1, int(settings.transcribe_pipeline_workers))
                self.executor = ThreadPoolExecutor(
                    max_workers=workers,
                    thread_name_prefix=f"voice-{self.session_id[:8]}",
                )
            executor = self.executor

        future = executor.submit(
            self._process_snapshot,
            seq,
            snapshot,
            content_type,
            model_id,
        )
        with self.lock:
            self.futures[seq] = future

        def _on_done(fut: Future, done_seq: int = seq) -> None:
            try:
                outcome = fut.result()
                with self.lock:
                    self.outcomes[done_seq] = outcome
            except Exception as exc:  # noqa: BLE001
                logger.warning("voice chunk seq=%s failed: %s", done_seq, exc)

        future.add_done_callback(_on_done)
        latest = self.latest_outcome()
        return {
            "accepted": True,
            "seq": seq,
            "buffer_bytes": len(snapshot),
            "interim_text": latest.text if latest else "",
            "interim_seq": latest.seq if latest else None,
            "interim_stage": latest.stage if latest else None,
            "pending": self.pending_count(),
        }

    def _process_snapshot(
        self,
        seq: int,
        snapshot: bytes,
        content_type: str,
        model_id: str | None,
    ) -> ChunkOutcome:
        started = time.perf_counter()
        from app.services.transcription import asr_bytes_only

        raw = asr_bytes_only(
            audio_bytes=snapshot,
            filename=f"stream-{seq}.webm",
            content_type=content_type,
            model_id=model_id,
        )
        corrected = multi_stage_correct(raw)
        elapsed_ms = (time.perf_counter() - started) * 1000
        logger.info(
            "voice chunk done session=%s seq=%s stage=%s (%.0fms)",
            self.session_id,
            seq,
            corrected.stage,
            elapsed_ms,
        )
        return ChunkOutcome(
            seq=seq,
            text=corrected.text,
            stage=corrected.stage,
            raw_asr=raw,
            elapsed_ms=elapsed_ms,
        )

    def pending_count(self) -> int:
        with self.lock:
            return sum(1 for fut in self.futures.values() if not fut.done())

    def latest_outcome(self) -> ChunkOutcome | None:
        with self.lock:
            if not self.outcomes:
                return None
            return self.outcomes[max(self.outcomes)]

    def finalize(self, *, wait_seconds: float | None = None) -> dict[str, Any]:
        """
        等待进行中任务（有上限），取最高 seq 结果；若无结果则对全量缓冲再跑一次。
        """
        timeout = (
            wait_seconds
            if wait_seconds is not None
            else float(settings.transcribe_stream_finalize_wait_seconds)
        )
        with self.lock:
            futures = list(self.futures.items())
            snapshot = bytes(self.buffer)
            content_type = self.mime
            model_id = self.model_id

        deadline = time.time() + max(0.1, timeout)
        for seq, fut in futures:
            remaining = deadline - time.time()
            if remaining <= 0:
                break
            try:
                fut.result(timeout=remaining)
            except Exception:  # noqa: BLE001
                logger.debug("voice finalize wait seq=%s skipped", seq, exc_info=True)

        latest = self.latest_outcome()
        if latest and latest.text.strip():
            self.close()
            return {
                "text": latest.text.strip(),
                "raw": (latest.raw_asr or "").strip(),
                "stage": latest.stage,
                "changed": latest.text.strip() != (latest.raw_asr or "").strip(),
                "seq": latest.seq,
                "source": "parallel_chunks",
            }

        # 无可用分片结果：全量再转一次
        if not snapshot:
            self.close()
            return {
                "text": "",
                "raw": "",
                "stage": "empty",
                "changed": False,
                "seq": None,
                "source": "empty",
            }

        from app.services.transcription import asr_bytes_only

        raw = asr_bytes_only(
            audio_bytes=snapshot,
            filename="stream-final.webm",
            content_type=content_type,
            model_id=model_id,
        )
        corrected = multi_stage_correct(raw)
        self.close()
        return {
            "text": corrected.text,
            "raw": corrected.raw,
            "stage": corrected.stage,
            "changed": corrected.changed,
            "seq": None,
            "source": "final_full",
        }

    def close(self) -> None:
        with self.lock:
            executor = self.executor
            self.executor = None
        if executor is not None:
            executor.shutdown(wait=False, cancel_futures=False)


class StreamSessionStore:
    """进程内会话表（短生命周期）。"""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._sessions: dict[str, StreamSession] = {}

    def create(self, *, model_id: str | None = None) -> StreamSession:
        self._purge_expired()
        session_id = uuid.uuid4().hex
        session = StreamSession(session_id=session_id, model_id=model_id)
        with self._lock:
            self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> StreamSession | None:
        with self._lock:
            return self._sessions.get(session_id)

    def remove(self, session_id: str) -> None:
        with self._lock:
            session = self._sessions.pop(session_id, None)
        if session:
            session.close()

    def _purge_expired(self) -> None:
        ttl = max(60, int(settings.transcribe_stream_session_ttl_seconds))
        now = time.time()
        with self._lock:
            expired = [sid for sid, sess in self._sessions.items() if now - sess.created_at > ttl]
        for sid in expired:
            self.remove(sid)


_STORE: StreamSessionStore | None = None
_STORE_LOCK = threading.Lock()


def get_stream_session_store() -> StreamSessionStore:
    global _STORE
    with _STORE_LOCK:
        if _STORE is None:
            _STORE = StreamSessionStore()
        return _STORE
