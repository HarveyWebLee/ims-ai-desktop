"""P2-3：按意图在已启用 catalog 模型中选型（仅允许目录内模型）。"""

from __future__ import annotations

from typing import Any

from app.models.catalog import get_catalog_item, get_default_model_id, get_enabled_models

AUTO_MODEL_ID = "auto"

# 偏重任务：多步 / 写操作 / 分析
_HEAVY_HINTS = (
    "导出",
    "批量",
    "计划",
    "分析",
    "处置",
    "处理告警",
    "编写",
    "生成报告",
    "对比",
    "总结",
    "方案",
    "排查",
    "修复",
    "修改",
    "删除",
    "确认执行",
)

# 偏轻任务：查询 / 导航
_LIGHT_HINTS = (
    "打开",
    "跳转",
    "导航",
    "查询",
    "查一下",
    "查下",
    "多少",
    "列表",
    "详情",
    "状态",
    "是什么",
    "有没有",
)


def _scenario_of(item: dict[str, Any]) -> str:
    key = str(item.get("scenarioKey") or "")
    if key.endswith(".light") or key == "light":
        return "light"
    if key.endswith(".default") or key == "default":
        return "default"
    return ""


def _first_enabled_for_scenario(scenario: str) -> str | None:
    for item in get_enabled_models():
        if _scenario_of(item) == scenario:
            mid = str(item.get("modelId") or "").strip()
            if mid and get_catalog_item(mid):
                return mid
    return None


def route_model_for_message(message: str) -> str:
    """
    仅从 enabled catalog 选型。
    轻任务 → scenario=light；重任务 / 默认 → isDefault 或 scenario=default。
    """
    text = (message or "").strip()
    light_id = _first_enabled_for_scenario("light")
    heavy_id = _first_enabled_for_scenario("default") or get_default_model_id()

    heavy_hit = any(h in text for h in _HEAVY_HINTS) or len(text) > 120
    light_hit = any(h in text for h in _LIGHT_HINTS) or (0 < len(text) <= 36)

    if heavy_hit:
        return heavy_id
    if light_hit and light_id:
        return light_id
    return heavy_id


def resolve_request_model_id(
    requested: str | None,
    *,
    user_message: str | None = None,
) -> tuple[str | None, str | None]:
    """
    解析请求 model_id。

    返回:
        (model_id, error_message)
        error_message 非空表示非法（不在目录或已禁用）。
    """
    from app.config import settings

    raw = (requested or "").strip()
    if not raw:
        raw = AUTO_MODEL_ID if settings.agent_model_route_enabled else get_default_model_id()

    if raw == AUTO_MODEL_ID:
        if not settings.agent_model_route_enabled:
            return get_default_model_id(), None
        return route_model_for_message(user_message or ""), None

    if not get_catalog_item(raw):
        return None, "model_id 不在模型目录中或已禁用"
    return raw, None
