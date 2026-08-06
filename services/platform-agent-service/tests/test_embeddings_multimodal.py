"""多模态 Embedding 路由与解析单测。"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.infrastructure.vector.embeddings import (
    DashScopeMultimodalEmbeddings,
    _is_multimodal_vl_model,
    resolve_embeddings,
)


def test_is_multimodal_vl_model():
    assert _is_multimodal_vl_model("qwen3-vl-embedding")
    assert _is_multimodal_vl_model("qwen2.5-vl-embedding")
    assert not _is_multimodal_vl_model("qwen3.7-text-embedding")
    assert not _is_multimodal_vl_model("text-embedding-v1")


def test_dashscope_multimodal_embed_documents_orders_by_index():
    embedder = DashScopeMultimodalEmbeddings(
        api_key="sk-test",
        model="qwen3-vl-embedding",
        dimensions=1536,
    )
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "output": {
            "embeddings": [
                {"index": 1, "embedding": [0.2, 0.3], "type": "text"},
                {"index": 0, "embedding": [0.0, 0.1], "type": "text"},
            ]
        }
    }

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = False
    mock_client.post.return_value = mock_resp

    with patch("app.infrastructure.vector.embeddings.httpx.Client", return_value=mock_client):
        vectors = embedder.embed_documents(["a", "b"])

    assert vectors == [[0.0, 0.1], [0.2, 0.3]]
    payload = mock_client.post.call_args.kwargs["json"]
    assert payload["model"] == "qwen3-vl-embedding"
    assert payload["parameters"]["dimension"] == 1536
    assert payload["input"]["contents"] == [{"text": "a"}, {"text": "b"}]


def test_resolve_embeddings_routes_vl_model():
    with (
        patch("app.infrastructure.vector.embeddings.settings") as mock_settings,
    ):
        mock_settings.embedding_provider = "dashscope"
        mock_settings.embedding_model = "qwen3-vl-embedding"
        mock_settings.dashscope_api_key = "sk-x"
        mock_settings.qdrant_vector_size = 1536
        mock_settings.deepseek_api_key = ""
        emb = resolve_embeddings()
    assert isinstance(emb, DashScopeMultimodalEmbeddings)
    assert emb.dimensions == 1536
