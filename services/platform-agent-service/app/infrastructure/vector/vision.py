"""
知识库图片视觉理解：DashScope 多模态（OpenAI 兼容）抽文字 / 描述。

流程：图片 → VL 模型文本 → 再走与普通文档相同的 Embedding / Qdrant 入库。
"""

from __future__ import annotations

import base64
import io
import logging
import mimetypes
from pathlib import Path

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_COMPAT_CHAT_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

_IMAGE_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
}


class VisionExtractError(Exception):
    """图片视觉抽取失败。"""


def _guess_mime(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in _IMAGE_MIME:
        return _IMAGE_MIME[suffix]
    guessed, _ = mimetypes.guess_type(path.name)
    if guessed and guessed.startswith("image/"):
        return guessed
    return "image/jpeg"


def _load_image_data_uri(path: Path, *, max_side: int) -> str:
    """读取图片，必要时缩小边长后转为 data URI。"""
    raw = path.read_bytes()
    max_bytes = max(1, settings.knowledge_image_max_bytes)
    if len(raw) > max_bytes:
        raise VisionExtractError(f"图片过大 {len(raw)} bytes，上限 {max_bytes}（{path.name}）")

    mime = _guess_mime(path)
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(raw))
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
            mime = "image/jpeg"
        w, h = img.size
        if max(w, h) > max_side:
            ratio = max_side / float(max(w, h))
            img = img.resize((max(1, int(w * ratio)), max(1, int(h * ratio))))
        buf = io.BytesIO()
        fmt = "JPEG" if mime == "image/jpeg" else ("PNG" if mime == "image/png" else "JPEG")
        if fmt == "JPEG":
            mime = "image/jpeg"
            img.save(buf, format=fmt, quality=85, optimize=True)
        else:
            img.save(buf, format=fmt, optimize=True)
        raw = buf.getvalue()
    except ImportError:
        logger.debug("Pillow 不可用，原图上传: %s", path)
    except Exception as exc:  # noqa: BLE001
        logger.warning("图片预处理失败，尝试原图上传 %s: %s", path, exc)

    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{b64}"


def extract_image_text(path: Path | str) -> str:
    """
    调用 DashScope VL 模型，抽取图中文字并简述示意图内容。

    需配置 ``DASHSCOPE_API_KEY``，且 ``knowledge_vision_enabled=true``。
    """
    if not settings.knowledge_vision_enabled:
        raise VisionExtractError("未启用图片入库（KNOWLEDGE_VISION_ENABLED=false）")

    api_key = (settings.dashscope_api_key or "").strip()
    if not api_key:
        raise VisionExtractError("未配置 DASHSCOPE_API_KEY，无法对图片做视觉抽取")

    file_path = Path(path)
    data_uri = _load_image_data_uri(
        file_path, max_side=max(256, settings.knowledge_vision_max_side)
    )
    model = (settings.knowledge_vision_model or "qwen-vl-plus").strip()
    prompt = (
        "你是知识库入库助手。请处理这张图片：\n"
        "1) 完整提取图中全部可见文字（含表格单元格，按阅读顺序）；\n"
        "2) 若存在表格，用 Markdown 表格输出；\n"
        "3) 若为示意图/架构图/界面截图，用中文简要描述主题、模块关系与关键标注；\n"
        "4) 不要编造图中不存在的内容。\n"
        f"文件名：{file_path.name}"
    )

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": data_uri}},
                    {"type": "text", "text": prompt},
                ],
            }
        ],
        "temperature": 0.1,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    timeout = float(settings.knowledge_vision_timeout_seconds)
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(_COMPAT_CHAT_URL, headers=headers, json=payload)
    except httpx.HTTPError as exc:
        raise VisionExtractError(f"视觉 API 请求失败: {exc}") from exc

    if resp.status_code >= 400:
        raise VisionExtractError(f"视觉 API HTTP {resp.status_code}: {resp.text[:500]}")

    data = resp.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise VisionExtractError(f"视觉 API 响应无法解析: {data!r}"[:800]) from exc

    if isinstance(content, list):
        # 部分多模态响应为分段列表
        texts = []
        for part in content:
            if isinstance(part, dict) and part.get("text"):
                texts.append(str(part["text"]))
            elif isinstance(part, str):
                texts.append(part)
        text = "\n".join(texts).strip()
    else:
        text = str(content or "").strip()

    if not text:
        raise VisionExtractError(f"视觉模型返回空文本: {file_path.name}")
    return f"[图片 {file_path.name}]\n{text}"
