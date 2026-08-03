"""
Realtime ASR WebSocket 桥接：浏览器 ↔ Agent ↔ DashScope qwen3-asr-flash-realtime。

按段协议（见 docs/architecture/10-voice-asr.md）：
- 录音中：转发 PCM；partial 仅推当前未落定句预览
- VAD 落定一句 → segment(pending) → 异步 multi_stage_correct → segment(done)
- 停录后：等待 in-flight 段纠错，汇总 final；不再对全文二次纠错
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from app.config import settings

logger = logging.getLogger(__name__)


def _event_id() -> str:
    return f"event_{uuid.uuid4().hex[:16]}"


def _preview_text(payload: dict[str, Any]) -> str:
    """单句预览：已确认前缀 + stash 草稿（官方推荐拼接）。"""
    confirmed = str(payload.get("text") or "")
    stash = str(payload.get("stash") or "")
    return f"{confirmed}{stash}".strip()


def _join_asr_parts(*parts: str) -> str:
    """跨句拼接：中文 ASR 片段直接相连，不插入空格。"""
    out: list[str] = []
    for part in parts:
        text = (part or "").strip()
        if text:
            out.append(text)
    return "".join(out)


def _segment_payload(
    *,
    seq: int,
    raw: str,
    text: str,
    status: str,
    changed: bool = False,
    stage: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "type": "segment",
        "seq": seq,
        "raw": raw,
        "text": text,
        "status": status,
        "changed": changed,
    }
    if stage is not None:
        payload["stage"] = stage
    return payload


def _segments_snapshot(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """按 seq 输出可序列化段列表。"""
    ordered = sorted(segments, key=lambda s: int(s["seq"]))
    return [
        {
            "seq": int(s["seq"]),
            "raw": str(s.get("raw") or ""),
            "text": str(s.get("text") or ""),
            "stage": s.get("stage"),
            "changed": bool(s.get("changed")),
            "status": str(s.get("status") or "done"),
        }
        for s in ordered
    ]


def _committed_text(segments: list[dict[str, Any]]) -> str:
    ordered = sorted(segments, key=lambda s: int(s["seq"]))
    return _join_asr_parts(*(str(s.get("text") or "") for s in ordered))


def _prior_context(segments: list[dict[str, Any]], seq: int) -> str:
    """本段之前已完成（或已有 text）段的拼接，供检索/LLM 上下文。"""
    prior = [
        str(s.get("text") or "")
        for s in sorted(segments, key=lambda x: int(x["seq"]))
        if int(s["seq"]) < seq and str(s.get("text") or "").strip()
    ]
    return _join_asr_parts(*prior)


async def handle_realtime_transcribe(websocket: WebSocket) -> None:
    """
    浏览器协议（JSON）：
      ← {type: ready}
      → {type: audio, data: base64_pcm16}
      → {type: stop}
      ← {type: partial, preview}
      ← {type: segment, seq, raw, text, status, changed, stage?}
      ← {type: final, text, segments}
      ← {type: error, message}
    """
    await websocket.accept()

    if not settings.transcribe_realtime_enabled:
        await websocket.send_json({"type": "error", "message": "Realtime ASR 未启用"})
        await websocket.close()
        return

    api_key = (settings.dashscope_api_key or "").strip()
    if not api_key:
        await websocket.send_json({"type": "error", "message": "未配置 DASHSCOPE_API_KEY"})
        await websocket.close()
        return

    model = (settings.transcribe_realtime_model or "qwen3-asr-flash-realtime").strip()
    base = (settings.transcribe_realtime_ws_url or "").rstrip("/")
    upstream_url = f"{base}?model={model}"
    sample_rate = int(settings.transcribe_realtime_sample_rate or 16000)

    import websockets
    from websockets.exceptions import ConnectionClosed

    segments: list[dict[str, Any]] = []
    correct_tasks: dict[int, asyncio.Task[None]] = {}
    current_preview = ""
    stop_requested = asyncio.Event()
    upstream_done = asyncio.Event()
    send_lock = asyncio.Lock()

    async def _safe_send(payload: dict[str, Any]) -> None:
        async with send_lock:
            try:
                await websocket.send_json(payload)
            except Exception:  # noqa: BLE001
                logger.debug("realtime send failed type=%s", payload.get("type"))

    async def _run_segment_correct(seq: int, raw: str) -> None:
        context = _prior_context(segments, seq)
        try:
            from app.services.voice.pipeline import multi_stage_correct

            corrected = await asyncio.to_thread(
                multi_stage_correct,
                raw,
                context=context,
            )
            text = corrected.text
            stage = corrected.stage
            changed = corrected.changed
        except Exception as exc:  # noqa: BLE001
            logger.warning("realtime segment correct failed seq=%s: %s", seq, exc)
            text = raw
            stage = "passthrough"
            changed = False

        for item in segments:
            if int(item["seq"]) == seq:
                item["text"] = text
                item["stage"] = stage
                item["changed"] = changed
                item["status"] = "done"
                break

        await _safe_send(
            _segment_payload(
                seq=seq,
                raw=raw,
                text=text,
                status="done",
                changed=changed,
                stage=stage,
            )
        )

    def _schedule_correct(seq: int, raw: str) -> None:
        task = asyncio.create_task(_run_segment_correct(seq, raw))
        correct_tasks[seq] = task

        def _cleanup(done: asyncio.Task[None], done_seq: int = seq) -> None:
            correct_tasks.pop(done_seq, None)
            _ = done.exception() if done.done() and not done.cancelled() else None

        task.add_done_callback(_cleanup)

    async def _append_segment(raw: str) -> int:
        seq = len(segments)
        item = {
            "seq": seq,
            "raw": raw,
            "text": raw,
            "stage": None,
            "changed": False,
            "status": "pending",
        }
        segments.append(item)
        await _safe_send(
            _segment_payload(
                seq=seq,
                raw=raw,
                text=raw,
                status="pending",
                changed=False,
            )
        )
        _schedule_correct(seq, raw)
        return seq

    try:
        async with websockets.connect(
            upstream_url,
            additional_headers=[
                ("Authorization", f"Bearer {api_key}"),
                ("OpenAI-Beta", "realtime=v1"),
            ],
            max_size=8 * 1024 * 1024,
            open_timeout=15,
        ) as upstream:
            session_update = {
                "event_id": _event_id(),
                "type": "session.update",
                "session": {
                    "modalities": ["text"],
                    "input_audio_format": "pcm",
                    "sample_rate": sample_rate,
                    "input_audio_transcription": {"language": "zh"},
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.0,
                        "silence_duration_ms": 800,
                    },
                },
            }
            await upstream.send(json.dumps(session_update, ensure_ascii=False))
            await _safe_send({"type": "ready", "model": model})

            async def pump_upstream() -> None:
                nonlocal current_preview
                try:
                    async for raw_msg in upstream:
                        if isinstance(raw_msg, bytes):
                            continue
                        try:
                            data = json.loads(raw_msg)
                        except json.JSONDecodeError:
                            continue
                        etype = data.get("type")
                        if etype == "conversation.item.input_audio_transcription.text":
                            preview = _preview_text(data)
                            if not preview:
                                continue
                            current_preview = preview
                            await _safe_send({"type": "partial", "preview": preview})
                        elif etype == "conversation.item.input_audio_transcription.completed":
                            transcript = str(data.get("transcript") or "").strip()
                            current_preview = ""
                            if transcript:
                                await _append_segment(transcript)
                            else:
                                await _safe_send({"type": "partial", "preview": ""})
                        elif etype == "error":
                            err = data.get("error") or {}
                            msg = err.get("message") if isinstance(err, dict) else str(data)
                            await _safe_send({"type": "error", "message": msg or "上游 ASR 错误"})
                        elif etype == "session.finished":
                            break
                except ConnectionClosed:
                    logger.debug("dashscope realtime upstream closed")
                finally:
                    upstream_done.set()

            async def pump_client() -> None:
                try:
                    while True:
                        message = await websocket.receive()
                        if message.get("type") == "websocket.disconnect":
                            stop_requested.set()
                            break
                        text = message.get("text")
                        if not text:
                            continue
                        try:
                            payload = json.loads(text)
                        except json.JSONDecodeError:
                            continue
                        mtype = payload.get("type")
                        if mtype == "audio":
                            audio_b64 = payload.get("data")
                            if not audio_b64:
                                continue
                            await upstream.send(
                                json.dumps(
                                    {
                                        "event_id": _event_id(),
                                        "type": "input_audio_buffer.append",
                                        "audio": audio_b64,
                                    },
                                    ensure_ascii=False,
                                )
                            )
                        elif mtype == "stop":
                            stop_requested.set()
                            await upstream.send(
                                json.dumps(
                                    {
                                        "event_id": _event_id(),
                                        "type": "session.finish",
                                    }
                                )
                            )
                            break
                except WebSocketDisconnect:
                    stop_requested.set()
                    try:
                        await upstream.send(
                            json.dumps({"event_id": _event_id(), "type": "session.finish"})
                        )
                    except Exception:  # noqa: BLE001
                        pass

            await asyncio.gather(pump_upstream(), pump_client())

            try:
                await asyncio.wait_for(upstream_done.wait(), timeout=8.0)
            except TimeoutError:
                logger.warning("realtime ASR wait session.finished timeout")

    except Exception as exc:  # noqa: BLE001
        logger.exception("realtime ASR bridge failed")
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
        except Exception:  # noqa: BLE001
            pass
        try:
            await websocket.close()
        except Exception:  # noqa: BLE001
            pass
        return

    # 停在半句：把当前预览升为最后一段并纠错
    leftover = (current_preview or "").strip()
    if leftover:
        await _append_segment(leftover)
        current_preview = ""

    if correct_tasks:
        wait_timeout = max(3.0, float(settings.transcribe_correct_timeout_seconds) + 4.0)
        try:
            await asyncio.wait_for(
                asyncio.gather(*correct_tasks.values(), return_exceptions=True),
                timeout=wait_timeout,
            )
        except TimeoutError:
            logger.warning("realtime segment correct wait timeout")
            for seq, task in list(correct_tasks.items()):
                if not task.done():
                    task.cancel()
                for item in segments:
                    if int(item["seq"]) == seq and item.get("status") != "done":
                        item["status"] = "done"
                        item["text"] = str(item.get("raw") or "")
                        item["stage"] = "passthrough"
                        item["changed"] = False
                        await _safe_send(
                            _segment_payload(
                                seq=seq,
                                raw=str(item.get("raw") or ""),
                                text=str(item.get("text") or ""),
                                status="done",
                                changed=False,
                                stage="passthrough",
                            )
                        )

    snap = _segments_snapshot(segments)
    final_text = _committed_text(segments)
    await _safe_send({"type": "final", "text": final_text, "segments": snap})

    try:
        await websocket.close()
    except Exception:  # noqa: BLE001
        pass
