"""
Embedding 模型解析：DashScope / DeepSeek 等。

- 文本模型（如 ``qwen3.7-text-embedding``）：OpenAI 兼容 ``/embeddings``
- 多模态 ``qwen3-vl-embedding``：须走 DashScope 原生 Multimodal Embedding API
  （不支持 compatible-mode），维度与 ``QDRANT_VECTOR_SIZE`` 对齐（支持 2560/2048/1536/1024/…）
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_MULTIMODAL_EMBED_URL = (
    "https://dashscope.aliyuncs.com/api/v1/services/embeddings/"
    "multimodal-embedding/multimodal-embedding"
)
# qwen3-vl-embedding：单次 contents 元素总数不超过 20
_MULTIMODAL_BATCH_SIZE = 20

_VL_EMBEDDING_MODELS = frozenset(
    {
        "qwen3-vl-embedding",
        "qwen2.5-vl-embedding",
    }
)


def _provider_base_url(provider: str) -> str:
    mapping = {
        "deepseek": "https://api.deepseek.com/v1",
        "dashscope": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    }
    return mapping.get(provider, "")


def _provider_api_key(provider: str) -> str:
    mapping = {
        "deepseek": settings.deepseek_api_key,
        "dashscope": settings.dashscope_api_key,
    }
    return mapping.get(provider, "")


def _is_multimodal_vl_model(model: str) -> bool:
    name = (model or "").strip().lower()
    return name in _VL_EMBEDDING_MODELS or name.endswith("-vl-embedding")


class DashScopeMultimodalEmbeddings:
    """
    DashScope 多模态 Embedding（文本路径）。

    实现 LangChain Embeddings 所需的 ``embed_documents`` / ``embed_query``，
    供文档知识库与实体同步复用；当前入库仍以文本切块为主。
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        dimensions: int,
        timeout_seconds: float = 60.0,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.dimensions = dimensions
        self.timeout_seconds = timeout_seconds

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        out: list[list[float]] = []
        for start in range(0, len(texts), _MULTIMODAL_BATCH_SIZE):
            batch = texts[start : start + _MULTIMODAL_BATCH_SIZE]
            out.extend(self._embed_batch(batch))
        return out

    def embed_query(self, text: str) -> list[float]:
        vectors = self._embed_batch([text or ""])
        return vectors[0]

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        contents = [{"text": t if t is not None else ""} for t in texts]
        payload: dict[str, Any] = {
            "model": self.model,
            "input": {"contents": contents},
            "parameters": {"dimension": int(self.dimensions)},
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                resp = client.post(_MULTIMODAL_EMBED_URL, headers=headers, json=payload)
        except httpx.HTTPError as exc:
            raise RuntimeError(f"DashScope 多模态 Embedding 网络失败: {exc}") from exc

        data = _safe_json(resp)
        if resp.status_code >= 400:
            message = _error_message(data) or resp.text
            raise RuntimeError(
                f"DashScope 多模态 Embedding 失败 HTTP {resp.status_code}: {message}"
            )
        if isinstance(data, dict) and data.get("code"):
            raise RuntimeError(
                f"DashScope 多模态 Embedding 错误: {data.get('code')} — {data.get('message')}"
            )

        embeddings = (
            (data.get("output") or {}).get("embeddings") if isinstance(data, dict) else None
        )
        if not isinstance(embeddings, list) or not embeddings:
            raise RuntimeError("DashScope 多模态 Embedding 返回空 embeddings")

        by_index: dict[int, list[float]] = {}
        for item in embeddings:
            if not isinstance(item, dict):
                continue
            idx = int(item.get("index", len(by_index)))
            vec = item.get("embedding")
            if not isinstance(vec, list) or not vec:
                raise RuntimeError(f"DashScope Embedding 第 {idx} 条向量为空")
            by_index[idx] = [float(x) for x in vec]

        ordered: list[list[float]] = []
        for i in range(len(texts)):
            if i not in by_index:
                raise RuntimeError(f"DashScope Embedding 缺少 index={i} 的向量")
            ordered.append(by_index[i])
        return ordered


def _safe_json(resp: httpx.Response) -> Any:
    try:
        return resp.json()
    except Exception:  # noqa: BLE001
        return {"raw": resp.text}


def _error_message(data: Any) -> str:
    if not isinstance(data, dict):
        return ""
    err = data.get("error")
    if isinstance(err, dict):
        return str(err.get("message") or err.get("code") or "")
    return str(data.get("message") or data.get("code") or "")


def resolve_embeddings():
    """
    创建 Embedding 实例（OpenAI 兼容或 DashScope 多模态）。

    异常：
        ValueError — 缺少对应厂商 API Key 或未知 provider
    """
    provider = (settings.embedding_provider or "dashscope").strip().lower()
    api_key = _provider_api_key(provider)
    model = (settings.embedding_model or "").strip()
    if not api_key:
        raise ValueError(f"未配置 {provider} API Key，无法生成向量（请设置对应环境变量）")
    if not model:
        raise ValueError("未配置 EMBEDDING_MODEL")

    if provider == "dashscope" and _is_multimodal_vl_model(model):
        logger.info(
            "使用 DashScope 多模态 Embedding model=%s dim=%s",
            model,
            settings.qdrant_vector_size,
        )
        return DashScopeMultimodalEmbeddings(
            api_key=api_key,
            model=model,
            dimensions=int(settings.qdrant_vector_size),
        )

    from langchain_openai import OpenAIEmbeddings
    from pydantic import SecretStr

    base_url = _provider_base_url(provider)
    if not base_url:
        raise ValueError(f"不支持的 embedding provider: {provider}")

    # DashScope 兼容接口单次 batch 上限为 10；其它厂商沿用 LangChain 默认
    embed_kwargs: dict = {
        "model": model,
        "api_key": SecretStr(api_key),
        "base_url": base_url,
        "dimensions": settings.qdrant_vector_size,
        "check_embedding_ctx_length": False,
    }
    if provider == "dashscope":
        embed_kwargs["chunk_size"] = 10

    return OpenAIEmbeddings(**embed_kwargs)
