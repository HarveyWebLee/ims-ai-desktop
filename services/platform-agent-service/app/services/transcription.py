"""
语音转写服务（DashScope qwen3-asr-flash）。

文件职责
--------
把侧栏录到的音频字节转成中文文本，再当作普通用户消息进入 chat 流程。
ASR 成功后走多级纠错（Rule → Redis Cache → Dictionary → Vector → LLM）。

在 Agent 流程中的位置
--------------------
语音入口的前处理（位于 stream_chat 之前）：
  前端上传 audio blob / 流式分片
    → asr_bytes_only / stream session
    → multi_stage_correct
    → 与键盘输入一样走 POST /api/agent/chat → stream_chat

如何被调用
----------
- 语音转写 HTTP API：``transcribe_bytes(...)``
- 脚本/测试：``transcribe_file_path`` / ``save_upload_to_temp``

白话解释
--------
麦克风 → 云端听写员（DashScope ASR）→（知识库纠错）→ 一句话文字。
未配置 DASHSCOPE_API_KEY 时直接抛出 TranscriptionError。
纠错失败或未命中知识库时静默回退 ASR 原文。

外部依赖:
    - DashScope 多模态 API（需 DASHSCOPE_API_KEY）
    - Qdrant + 聊天模型（纠错可选，fail-open）

模型选择:
    优先 settings.transcribe_model，否则 catalog 中第一个 supportsAudio 模型，
    再否则默认 qwen3-asr-flash。
"""

from __future__ import annotations

# ── 标准库 ──
import base64
import mimetypes
import tempfile
from pathlib import Path
from typing import Any

# ── 第三方 ──
import httpx  # 现代 HTTP 客户端，支持 sync/async

# ── 项目内 ──
from app.config import settings
from app.models.catalog import load_catalog

# DashScope 多模态/ASR 接口（国内）
_DASHSCOPE_MULTIMODAL_URL = (
    "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
)

# 支持音频的 catalog 模型，优先 qwen3-asr-flash（专用 ASR，不在聊天 catalog 也可配置）
_DEFAULT_ASR_MODEL = "qwen3-asr-flash"


class TranscriptionError(Exception):
    """
    转写失败异常。

    调用方可 catch 此异常并向用户展示友好错误信息（API 层转 fail envelope）。
    """


def get_default_transcribe_model_id() -> str:
    """
    从 catalog 取第一个 supportsAudio 的 modelId，否则用默认 ASR 模型。

    返回:
        API 使用的 model 名字符串
    """
    if settings.transcribe_model:
        return settings.transcribe_model
    for item in load_catalog():
        if item.get("enabled", True) and item.get("supportsAudio"):
            return item.get("apiModelName") or item["modelId"]
    return _DEFAULT_ASR_MODEL


def _resolve_api_model(model_id: str | None) -> str:
    """
    将 catalog 的 model_id 映射为实际 DashScope ASR API model 名。

    业务规则:
        - 未传 model → 走默认
        - 专用 ASR（qwen3-asr-flash）用其 apiModelName
        - 其它 supportsAudio（如 Omni 聊天模型）仍统一走 qwen3-asr-flash，更稳

    抛出:
        TranscriptionError: model_id 不支持语音转写
    """
    if not model_id:
        return get_default_transcribe_model_id()
    for item in load_catalog():
        if item.get("modelId") == model_id and item.get("enabled", True):
            # 专用 ASR 优先；Omni 模型转写仍走 qwen3-asr-flash 更稳
            if item.get("modelId") == "qwen3-asr-flash":
                return item.get("apiModelName") or item["modelId"]
            if item.get("supportsAudio"):
                return _DEFAULT_ASR_MODEL
    if model_id in (_DEFAULT_ASR_MODEL, "qwen3-asr-flash"):
        return _DEFAULT_ASR_MODEL
    raise TranscriptionError(f"model_id 不支持语音转写: {model_id}")


def _guess_mime(filename: str | None, content_type: str | None) -> str:
    """
    推断音频 MIME 类型。

    参数:
        filename: 文件名（用于 mimetypes.guess_type）
        content_type: HTTP Content-Type 头

    返回:
        如 "audio/webm"、"audio/wav"；猜不到时默认 audio/webm
    """
    if content_type and content_type.startswith("audio/"):
        return content_type.split(";")[0].strip()  # 去掉 charset 等后缀
    if filename:
        guessed, _ = mimetypes.guess_type(filename)
        if guessed and guessed.startswith("audio/"):
            return guessed
    return "audio/webm"


def _to_data_uri(audio_bytes: bytes, mime: str) -> str:
    """
    将音频字节转为 data URI（DashScope API 要求的 inline 格式）。

    参数:
        audio_bytes: 原始音频二进制
        mime: MIME 类型

    返回:
        "data:audio/webm;base64,..." 格式字符串
    """
    encoded = base64.b64encode(audio_bytes).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _extract_text(payload: dict[str, Any]) -> str:
    """
    解析 DashScope multimodal-generation 响应，提取转写文本。

    兼容两种常见形状:
        - choices[0].message.content 为 str 或 [{text: ...}, ...]
        - output.text 直接给字符串

    抛出:
        TranscriptionError: 响应含错误码或文本为空
    """
    if payload.get("code") and payload.get("code") != "Success":
        msg = payload.get("message") or "DashScope 转写失败"
        raise TranscriptionError(str(msg))

    output = payload.get("output") or {}
    choices = output.get("choices") or []
    if choices:
        message = choices[0].get("message") or {}
        content = message.get("content")
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts: list[str] = []
            for block in content:
                if isinstance(block, dict) and block.get("text"):
                    parts.append(str(block["text"]))
            text = "".join(parts).strip()
            if text:
                return text

    # 部分 ASR 响应在 output.text
    if isinstance(output.get("text"), str):
        return output["text"].strip()

    raise TranscriptionError("转写结果为空")


def asr_bytes_only(
    *,
    audio_bytes: bytes,
    filename: str | None = None,
    content_type: str | None = None,
    model_id: str | None = None,
) -> str:
    """
    仅调用 DashScope ASR，不做多级纠错（供流式分片并行管线使用）。
    """
    if len(audio_bytes) > settings.transcribe_max_bytes:
        raise TranscriptionError(
            f"音频文件过大（最大 {settings.transcribe_max_bytes // 1024 // 1024}MB）"
        )
    if not audio_bytes:
        raise TranscriptionError("音频内容为空")

    if not settings.dashscope_api_key:
        raise TranscriptionError("未配置 DASHSCOPE_API_KEY，无法转写")

    api_model = _resolve_api_model(model_id)
    mime = _guess_mime(filename, content_type)
    data_uri = _to_data_uri(audio_bytes, mime)

    body = {
        "model": api_model,
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": [{"audio": data_uri}],
                }
            ]
        },
        "parameters": {
            "asr_options": {
                "enable_itn": True,
                "language": "zh",
            }
        },
    }

    headers = {
        "Authorization": f"Bearer {settings.dashscope_api_key}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=settings.transcribe_timeout_seconds) as client:
            resp = client.post(_DASHSCOPE_MULTIMODAL_URL, json=body, headers=headers)
            resp.raise_for_status()
            payload = resp.json()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:500] if exc.response else str(exc)
        raise TranscriptionError(f"DashScope 请求失败: {detail}") from exc
    except httpx.RequestError as exc:
        raise TranscriptionError(f"无法连接 DashScope: {exc}") from exc

    return _extract_text(payload)


def transcribe_bytes(
    *,
    audio_bytes: bytes,
    filename: str | None = None,
    content_type: str | None = None,
    model_id: str | None = None,
) -> str:
    """
    将音频字节转写为文本（主入口）：ASR + 多级纠错。
    """
    return transcribe_bytes_detail(
        audio_bytes=audio_bytes,
        filename=filename,
        content_type=content_type,
        model_id=model_id,
    ).text


def transcribe_bytes_detail(
    *,
    audio_bytes: bytes,
    filename: str | None = None,
    content_type: str | None = None,
    model_id: str | None = None,
):
    """
    转写并返回纠错详情（text / raw / stage / changed）。
    """
    from app.services.voice.pipeline import multi_stage_correct

    raw_text = asr_bytes_only(
        audio_bytes=audio_bytes,
        filename=filename,
        content_type=content_type,
        model_id=model_id,
    )
    return multi_stage_correct(raw_text)


def transcribe_file_path(path: Path, model_id: str | None = None) -> str:
    """
    从本地文件转写（测试/脚本用）。

    参数:
        path: 音频文件 Path 对象
        model_id: 可选模型 ID

    返回:
        转写文本
    """
    data = path.read_bytes()
    return transcribe_bytes(
        audio_bytes=data,
        filename=path.name,
        model_id=model_id,
    )


def save_upload_to_temp(audio_bytes: bytes, suffix: str = ".webm") -> Path:
    """
    临时保存上传音频到系统 temp 目录（调试/扩展用）。

    参数:
        audio_bytes: 音频内容
        suffix: 文件后缀，默认 .webm

    返回:
        临时文件 Path；调用方负责后续删除
    """
    fd, name = tempfile.mkstemp(suffix=suffix)
    import os

    os.close(fd)  # mkstemp 返回的文件描述符需手动关闭
    p = Path(name)
    p.write_bytes(audio_bytes)
    return p
