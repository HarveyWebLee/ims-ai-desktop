"""Plan 阶段 LLM 参数抽取与合并单测"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.llm_plan_params import (
    LlmPlanParamsOut,
    LlmToolParamsEntry,
    generate_llm_plan_params,
    merge_tool_params,
    normalize_llm_plan_params,
    sanitize_llm_tool_params,
)
from app.services.plan_confirm import merge_plan_params


class TestSanitizeLlmToolParams:
    def test_accepts_resolvable_absolute_range(self):
        params = sanitize_llm_tool_params(
            "query_alarms",
            {
                "start_time": "2026-07-02 11:00:00",
                "end_time": "2026-07-02 11:17:00",
            },
        )
        assert params["start_time"] == "2026-07-02 11:00:00"
        assert params["end_time"] == "2026-07-02 11:17:00"

    def test_rejects_unresolvable_time(self):
        params = sanitize_llm_tool_params(
            "query_alarms",
            {"start_time": "not-a-time", "end_time": ""},
        )
        assert "start_time" not in params


class TestMergePlanParams:
    def test_llm_overrides_empty_rule_params(self):
        steps = [
            {"id": "1", "tool": "query_alarms", "label": "查询"},
            {"id": "2", "tool": "download_file", "label": "导出"},
        ]
        msg = "查 7月2号 11:00 到 11:17 的告警并导出"
        merged = merge_plan_params(
            msg,
            steps,
            llm_params={
                "query_alarms": {
                    "start_time": "2026-07-02 11:00:00",
                    "end_time": "2026-07-02 11:17:00",
                },
                "download_file": {
                    "resource": "alarm_report",
                    "start_time": "2026-07-02 11:00:00",
                    "end_time": "2026-07-02 11:17:00",
                },
            },
        )
        assert merged["query_alarms"]["start_time"] == "2026-07-02 11:00:00"
        assert merged["download_file"]["end_time"] == "2026-07-02 11:17:00"

    def test_rule_skeleton_empty_when_llm_none(self):
        """无 LLM 抽参时规则层只给空槽，不再从原话填近三天。"""
        steps = [
            {"id": "1", "tool": "query_alarms", "label": "查询"},
            {"id": "2", "tool": "download_file", "label": "导出"},
        ]
        merged = merge_plan_params("查近三天告警然后导出", steps, llm_params=None)
        assert merged["query_alarms"]["start_time"] == ""
        assert merged["download_file"]["resource"] == ""


class TestMergeToolParams:
    def test_overlay_fills_missing_end(self):
        base = {"start_time": "2026-07-02 11:00:00", "end_time": ""}
        overlay = {"end_time": "2026-07-02 11:17:00"}
        merged = merge_tool_params(base, overlay)
        assert merged["end_time"] == "2026-07-02 11:17:00"


class TestGenerateLlmPlanParams:
    @pytest.mark.asyncio
    @patch("app.services.llm_plan_params.settings")
    async def test_disabled_skips(self, mock_settings):
        mock_settings.agent_llm_plan_enabled = False
        steps = [
            {"id": "1", "tool": "query_alarms", "label": "查"},
            {"id": "2", "tool": "download_file", "label": "导"},
        ]
        assert await generate_llm_plan_params("hello", steps, model_id="qwen3.5-35b-a3b") is None

    @pytest.mark.asyncio
    @patch("app.services.llm_plan_params.settings")
    @patch("app.models.router.resolve_chat_model")
    async def test_success(self, mock_resolve, mock_settings):
        mock_settings.agent_llm_plan_enabled = True
        structured = MagicMock()
        structured.ainvoke = AsyncMock(
            return_value=LlmPlanParamsOut(
                params=[
                    LlmToolParamsEntry(
                        tool="query_alarms",
                        start_time="2026-07-02 11:00:00",
                        end_time="2026-07-02 11:17:00",
                    ),
                    LlmToolParamsEntry(
                        tool="download_file",
                        resource="alarm_report",
                        start_time="2026-07-02 11:00:00",
                        end_time="2026-07-02 11:17:00",
                    ),
                ]
            )
        )
        model = MagicMock()
        model.with_structured_output.return_value = structured
        mock_resolve.return_value = model

        steps = [
            {"id": "1", "tool": "query_alarms", "label": "查"},
            {"id": "2", "tool": "download_file", "label": "导"},
        ]
        result = await generate_llm_plan_params(
            "7月2号 11:00 到 11:17 查告警并导出",
            steps,
            model_id="qwen3.5-35b-a3b",
        )
        assert result is not None
        assert result["query_alarms"]["end_time"] == "2026-07-02 11:17:00"


class TestNormalizeLlmPlanParams:
    def test_ignores_tools_not_in_steps(self):
        steps = [{"id": "1", "tool": "query_alarms", "label": "查"}]
        out = normalize_llm_plan_params(
            [
                LlmToolParamsEntry(
                    tool="query_alarms",
                    start_time="2026-07-02 11:00:00",
                    end_time="2026-07-02 11:17:00",
                ),
                LlmToolParamsEntry(tool="navigate_to", path="/foo"),
            ],
            steps,
        )
        assert "query_alarms" in out
        assert "navigate_to" not in out
