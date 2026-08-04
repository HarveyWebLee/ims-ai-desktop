"""实体术语运营 API（stats / search）。"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api import entities as entities_api


@pytest.mark.asyncio
async def test_entity_stats_requires_auth():
    with patch(
        "app.api.entities.get_current_user_id",
        new_callable=AsyncMock,
        side_effect=HTTPException(status_code=401, detail="未授权"),
    ):
        with pytest.raises(HTTPException) as exc:
            await entities_api.entity_stats(authorization=None)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_entity_stats_when_qdrant_unconfigured():
    with (
        patch(
            "app.api.entities.get_current_user_id",
            new_callable=AsyncMock,
            return_value="u1",
        ),
        patch("app.infrastructure.vector.client.is_qdrant_configured", return_value=False),
    ):
        resp = await entities_api.entity_stats(authorization="Bearer x")
    assert resp["code"] == 0
    assert resp["data"]["enabled"] is False
    assert resp["data"]["points"] == 0


@pytest.mark.asyncio
async def test_entity_search_returns_items():
    store = MagicMock()
    store.collection = "platform_entities"
    store.similarity_search.return_value = [
        {
            "score": 0.88,
            "entity_type": "device",
            "entity_key": "CHWP-01",
            "source": "dm:device:CHWP-01",
            "text": "设备编码：CHWP-01；设备名称：冷冻水泵1号",
            "payload": {
                "device_code": "CHWP-01",
                "device_name": "冷冻水泵1号",
                "table": "p_device",
            },
        }
    ]

    with (
        patch(
            "app.api.entities.get_current_user_id",
            new_callable=AsyncMock,
            return_value="u1",
        ),
        patch("app.api.entities._entity_store", return_value=store),
    ):
        body = entities_api.EntitySearchBody(query="冷冻水泵", limit=5, entity_types=["device"])
        resp = await entities_api.entity_search(body, authorization="Bearer x")

    assert resp["code"] == 0
    assert resp["data"]["items"][0]["entity_key"] == "CHWP-01"
    assert resp["data"]["items"][0]["device_name"] == "冷冻水泵1号"
    store.similarity_search.assert_called_once_with(
        "冷冻水泵",
        limit=5,
        entity_types=["device"],
    )
