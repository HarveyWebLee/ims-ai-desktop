"""显式 Plan（plan_first）覆盖 AI-first 旁路。"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.graph.parent_graph import classify_node
from app.services.plan_confirm import plan_needs_user_confirm
from contracts.context import current_plan_first


@pytest.mark.asyncio
async def test_classify_ai_first_default_react(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "agent_intent_ai_first", True)
    token = current_plan_first.set(False)
    try:
        out = await classify_node(
            {
                "user_message": "查近三天告警然后导出",
                "llm_user_message": "查近三天告警然后导出",
                "model_id": "qwen3.5-35b-a3b",
                "metadata": {},
            }
        )
        assert out == {"route": "react"}
    finally:
        current_plan_first.reset(token)


@pytest.mark.asyncio
async def test_classify_plan_first_routes_plan_confirm(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import settings
    from app.services.plan_confirm import PlanConfirmGate

    monkeypatch.setattr(settings, "agent_intent_ai_first", True)
    gate = PlanConfirmGate(
        steps=[{"id": "1", "label": "查询", "tool": "query_alarms", "status": "awaiting_confirm"}],
        params_by_tool={},
        interrupt_payload={"type": "plan_confirm", "tool": "__plan__", "steps": []},
        resume_hint={},
    )
    token = current_plan_first.set(True)
    try:
        with (
            patch(
                "app.services.plan_confirm.prepare_plan_confirm_gate_async",
                new=AsyncMock(return_value=gate),
            ),
            patch(
                "app.services.device_control_gate.prepare_device_control_hitl_gate",
                return_value=None,
            ),
        ):
            out = await classify_node(
                {
                    "user_message": "查近三天告警然后导出",
                    "llm_user_message": "查近三天告警然后导出",
                    "model_id": "qwen3.5-35b-a3b",
                    "metadata": {},
                }
            )
        assert out["route"] == "plan_confirm"
        assert out["plan_confirm_payload"]["type"] == "plan_confirm"
    finally:
        current_plan_first.reset(token)


def test_plan_needs_confirm_when_plan_first(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "agent_plan_confirm_write_only", True)
    steps = [
        {"id": "1", "label": "查询", "tool": "query_alarms", "status": "pending"},
        {"id": "2", "label": "详情", "tool": "get_alarm_detail", "status": "pending"},
    ]
    token_off = current_plan_first.set(False)
    try:
        assert plan_needs_user_confirm(steps) is False
    finally:
        current_plan_first.reset(token_off)

    token_on = current_plan_first.set(True)
    try:
        assert plan_needs_user_confirm(steps) is True
    finally:
        current_plan_first.reset(token_on)
