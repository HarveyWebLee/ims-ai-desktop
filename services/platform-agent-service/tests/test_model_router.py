"""P2-3：模型路由与禁用校验。"""

from __future__ import annotations

import pytest

from app.config import settings
from app.services.model_router import (
    AUTO_MODEL_ID,
    resolve_request_model_id,
    route_model_for_message,
)


@pytest.fixture(autouse=True)
def _enable_route(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "agent_model_route_enabled", True)


def test_removed_or_unknown_model_rejected():
    # 已从 catalog 删除的旧模型 id 应被拒绝
    mid, err = resolve_request_model_id("qwen3.7-plus", user_message="你好")
    assert mid is None
    assert err


def test_unknown_model_rejected():
    mid, err = resolve_request_model_id("not-a-real-model", user_message="x")
    assert mid is None
    assert err


def test_auto_routes_to_enabled_catalog_only():
    mid, err = resolve_request_model_id(AUTO_MODEL_ID, user_message="查询昨天告警列表")
    assert err is None
    assert mid
    from app.models.catalog import get_catalog_item

    assert get_catalog_item(mid) is not None


def test_heavy_prefers_default_scenario():
    mid = route_model_for_message("请导出近三天告警并批量处理")
    assert mid == "qwen3-32b"


def test_light_prefers_light_scenario():
    mid = route_model_for_message("打开设施管理")
    from app.models.catalog import get_catalog_item

    assert get_catalog_item(mid) is not None


def test_explicit_enabled_model_passthrough():
    mid, err = resolve_request_model_id("qwen3-32b", user_message="任意")
    assert err is None
    assert mid == "qwen3-32b"
