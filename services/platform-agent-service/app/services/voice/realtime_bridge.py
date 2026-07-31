"""
Realtime ASR WebSocket 桥接：浏览器 ↔ Agent ↔ DashScope qwen3-asr-flash-realtime。

- 录音中：转发 PCM，并把 transcription.text（text+stash）以 partial 推给前端
- Server VAD 会按静音切成多个 conversation item；每项的 text/stash/completed
  只覆盖「当前句」。必须把已完成句累加后再拼当前预览，否则后句会盖掉前句。
- 停止后：session.finish → 取全文 transcript → multi_stage_correct → final
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


def _display_transcript(committed: list[str], current_preview: str = "") -> str:
    """已落定各句 + 当前句预览 → 输入框应展示的全文。"""
    return _join_asr_parts(*committed, current_preview)


async def handle_realtime_transcribe(websocket: WebSocket) -> None:
    """
    浏览器协议（JSON）：
      ← {type: ready}
      → {type: audio, data: base64_pcm16}
      → {type: stop}
      ← {type: partial, text}   # 全文（已确认句 + 当前预览）
      ← {type: completed, text} # 全文（新一句落定后）
      ← {type: final, text, stage}
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

    # VAD 多句：committed 存各 item 的 completed；current_preview 为当前 item 的 text+stash
    committed: list[str] = []
    current_preview = ""
    last_partial = ""
    final_transcript = ""
    stop_requested = asyncio.Event()
    upstream_done = asyncio.Event()

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
                        # 略放宽，减少一句中间短停顿被切成新 item（仍靠累加兜底）
                        "silence_duration_ms": 800,
                    },
                },
            }
            await upstream.send(json.dumps(session_update, ensure_ascii=False))
            await websocket.send_json({"type": "ready", "model": model})

            async def pump_upstream() -> None:
                nonlocal last_partial, final_transcript, current_preview
                try:
                    async for raw in upstream:
                        if isinstance(raw, bytes):
                            continue
                        try:
                            data = json.loads(raw)
                        except json.JSONDecodeError:
                            continue
                        etype = data.get("type")
                        if etype == "conversation.item.input_audio_transcription.text":
                            preview = _preview_text(data)
                            if not preview:
                                continue
                            current_preview = preview
                            display = _display_transcript(committed, current_preview)
                            last_partial = display
                            await websocket.send_json({"type": "partial", "text": display})
                        elif etype == "conversation.item.input_audio_transcription.completed":
                            transcript = str(data.get("transcript") or "").strip()
                            if transcript:
                                committed.append(transcript)
                            current_preview = ""
                            display = _display_transcript(committed)
                            if display:
                                final_transcript = display
                                last_partial = display
                                await websocket.send_json({"type": "completed", "text": display})
                        elif etype == "error":
                            err = data.get("error") or {}
                            msg = err.get("message") if isinstance(err, dict) else str(data)
                            await websocket.send_json(
                                {"type": "error", "message": msg or "上游 ASR 错误"}
                            )
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

            # 等待上游收尾（最多数秒）
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

    # 停在半句时可能尚无 completed：优先用含当前预览的 last_partial
    raw = (last_partial or final_transcript or "").strip()
    if len(final_transcript) > len(raw):
        raw = final_transcript
    if not raw:
        await websocket.send_json({"type": "final", "text": "", "stage": "empty"})
        await websocket.close()
        return

    try:
        from app.services.voice.pipeline import multi_stage_correct

        corrected = await asyncio.to_thread(multi_stage_correct, raw)
        await websocket.send_json(
            {
                "type": "final",
                "text": corrected.text,
                "stage": corrected.stage,
                "raw": corrected.raw or raw,
                "changed": corrected.changed,
            }
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("realtime final correct failed: %s", exc)
        await websocket.send_json(
            {
                "type": "final",
                "text": raw,
                "stage": "passthrough",
                "raw": raw,
                "changed": False,
            }
        )

    try:
        await websocket.close()
    except Exception:  # noqa: BLE001
        pass
