"""
Embedding 模型解析：OpenAI 兼容协议对接 DashScope / DeepSeek 等。

默认使用 DashScope ``qwen3.7-text-embedding``（维度 1024，与 ``QDRANT_VECTOR_SIZE`` 对齐）。
"""

from __future__ import annotations

from app.config import settings


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


def resolve_embeddings():
    """
    创建 LangChain ``OpenAIEmbeddings`` 实例（OpenAI 兼容）。

    异常：
        ValueError — 缺少对应厂商 API Key 或未知 provider
    """
    from langchain_openai import OpenAIEmbeddings
    from pydantic import SecretStr

    provider = (settings.embedding_provider or "dashscope").strip().lower()
    api_key = _provider_api_key(provider)
    base_url = _provider_base_url(provider)
    if not base_url:
        raise ValueError(f"不支持的 embedding provider: {provider}")
    if not api_key:
        raise ValueError(f"未配置 {provider} API Key，无法生成向量（请设置对应环境变量）")

    # DashScope 兼容接口单次 batch 上限为 10；其它厂商沿用 LangChain 默认
    embed_kwargs: dict = {
        "model": settings.embedding_model,
        "api_key": SecretStr(api_key),
        "base_url": base_url,
        "dimensions": settings.qdrant_vector_size,
        "check_embedding_ctx_length": False,
    }
    if provider == "dashscope":
        embed_kwargs["chunk_size"] = 10

    return OpenAIEmbeddings(**embed_kwargs)
