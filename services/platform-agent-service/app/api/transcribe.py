"""
语音转写 API：一次性转写 + 流式分片并行。

- POST /api/agent/transcribe
- POST /api/agent/transcribe/stream/start
- POST /api/agent/transcribe/stream/chunk
- POST /api/agent/transcribe/stream/finish
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Form, UploadFile

from app.api.response import fail, ok
from app.config import settings
from app.services.transcription import TranscriptionError, transcribe_bytes_detail
from app.services.voice.stream_session import get_stream_session_store


async def transcribe_audio(
    file: UploadFile,
    model_id: Annotated[str | None, Form()] = None,
):
    """一次性上传转写（内部仍走多级纠错）。"""
    if not file or not file.filename:
        return fail(40004, "参数错误", "未上传音频文件")

    try:
        audio_bytes = await file.read()
    except Exception as exc:
        return fail(40005, "参数错误", f"读取音频失败: {exc}")

    try:
        result = transcribe_bytes_detail(
            audio_bytes=audio_bytes,
            filename=file.filename,
            content_type=file.content_type,
            model_id=model_id,
        )
    except TranscriptionError as exc:
        return fail(50010, "转写失败", str(exc))

    return ok(
        {
            "text": result.text,
            "raw": result.raw,
            "stage": result.stage,
            "changed": result.changed,
            "model_id": model_id,
            "segments": [
                {
                    "seq": 0,
                    "raw": result.raw,
                    "text": result.text,
                    "stage": result.stage,
                    "changed": result.changed,
                    "status": "done",
                }
            ],
        }
    )


async def stream_start(
    model_id: Annotated[str | None, Form()] = None,
):
    """创建流式转写会话。"""
    if not settings.transcribe_stream_enabled:
        return fail(40006, "未启用", "流式转写未开启（TRANSCRIBE_STREAM_ENABLED）")
    session = get_stream_session_store().create(model_id=model_id)
    return ok(
        {
            "session_id": session.session_id,
            "workers": settings.transcribe_pipeline_workers,
        }
    )


async def stream_chunk(
    file: UploadFile,
    session_id: Annotated[str, Form()],
    seq: Annotated[int, Form()],
    model_id: Annotated[str | None, Form()] = None,
):
    """
    提交一个音频分片：追加缓冲并并行启动 ASR+纠错，立即返回（不串行阻塞）。
    """
    if not settings.transcribe_stream_enabled:
        return fail(40006, "未启用", "流式转写未开启")
    if not file or not file.filename:
        return fail(40004, "参数错误", "未上传音频分片")
    store = get_stream_session_store()
    session = store.get(session_id)
    if session is None:
        return fail(40401, "会话不存在", "stream session 无效或已过期")
    if model_id:
        session.model_id = model_id

    try:
        audio_bytes = await file.read()
    except Exception as exc:
        return fail(40005, "参数错误", f"读取分片失败: {exc}")

    if not audio_bytes:
        return fail(40004, "参数错误", "音频分片为空")

    try:
        result = session.submit_chunk(
            seq=int(seq),
            audio_bytes=audio_bytes,
            mime=file.content_type,
        )
    except ValueError as exc:
        return fail(40004, "参数错误", str(exc))
    except Exception as exc:  # noqa: BLE001
        return fail(50010, "转写失败", str(exc))

    return ok(result)


async def stream_finish(
    session_id: Annotated[str, Form()],
):
    """等待并行分片收敛，返回最终文本。"""
    if not settings.transcribe_stream_enabled:
        return fail(40006, "未启用", "流式转写未开启")
    store = get_stream_session_store()
    session = store.get(session_id)
    if session is None:
        return fail(40401, "会话不存在", "stream session 无效或已过期")

    try:
        import asyncio

        result = await asyncio.to_thread(session.finalize)
    except TranscriptionError as exc:
        store.remove(session_id)
        return fail(50010, "转写失败", str(exc))
    except Exception as exc:  # noqa: BLE001
        store.remove(session_id)
        return fail(50010, "转写失败", str(exc))

    store.remove(session_id)
    return ok(
        {
            "text": result.get("text") or "",
            "raw": result.get("raw") or "",
            "stage": result.get("stage"),
            "changed": bool(result.get("changed")),
            "source": result.get("source"),
            "seq": result.get("seq"),
            "segments": result.get("segments") or [],
        }
    )
