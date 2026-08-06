"""Phase D1 LLM 任务规划单测"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.llm_task_planner import (
    LlmPlanStepOut,
    LlmTaskPlanOut,
    generate_llm_task_plan,
    normalize_llm_plan_steps,
    resolve_task_plan,
)


class TestNormalizeLlmPlanSteps:
    def test_filters_unknown_tools(self):
        steps = normalize_llm_plan_steps(
            [
                LlmPlanStepOut(id="1", label="查告警", tool="query_alarms"),
                LlmPlanStepOut(id="2", label="坏工具", tool="__bad__"),
                LlmPlanStepOut(id="3", label="导出", tool="download_file"),
            ]
        )
        assert len(steps) == 2
        assert steps[0]["tool"] == "query_alarms"
        assert steps[1]["status"] == "pending"


class TestGenerateLlmTaskPlan:
    @pytest.mark.asyncio
    @patch("app.services.llm_task_planner.settings")
    async def test_disabled_returns_none(self, mock_settings):
        mock_settings.agent_llm_plan_enabled = False
        result = await generate_llm_task_plan("查告警然后导出", model_id="qwen3.5-35b-a3b")
        assert result is None

    @pytest.mark.asyncio
    @patch("app.services.llm_task_planner.settings")
    @patch("app.models.router.resolve_chat_model")
    async def test_success_returns_steps(
        self,
        mock_resolve,
        mock_settings,
    ):
        mock_settings.agent_llm_plan_enabled = True
        structured = MagicMock()
        structured.ainvoke = AsyncMock(
            return_value=LlmTaskPlanOut(
                steps=[
                    LlmPlanStepOut(id="1", label="查询", tool="query_alarms"),
                    LlmPlanStepOut(id="2", label="导出", tool="download_file"),
                ]
            )
        )
        model = MagicMock()
        model.with_structured_output.return_value = structured
        mock_resolve.return_value = model

        result = await generate_llm_task_plan(
            "查近三天告警然后导出",
            model_id="qwen3.5-35b-a3b",
        )
        assert result is not None
        assert len(result) == 2


class TestResolveTaskPlan:
    @pytest.mark.asyncio
    @patch("app.services.llm_task_planner.settings")
    async def test_fallback_to_rules(self, mock_settings):
        mock_settings.agent_llm_plan_enabled = False
        plan = await resolve_task_plan(
            "查近三天告警然后导出",
            model_id="qwen3.5-35b-a3b",
        )
        assert plan is not None
        assert len(plan) >= 2
