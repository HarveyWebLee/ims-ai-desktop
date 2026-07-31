"""语音语义纠错：实体术语优先。"""

from __future__ import annotations

from unittest.mock import patch

from app.services.voice.semantic import (
    _apply_terms,
    _extract_entity_terms,
    apply_semantic_correction,
)


def test_extract_entity_terms_prefers_payload_fields() -> None:
    blocks = [
        {
            "title": "冷冻水泵1号",
            "terms": ["冷冻水泵1号", "CHWP-01", "出水温度", "Tout"],
            "text": "设备编码：CHWP-01；设备名称：冷冻水泵1号",
        }
    ]
    terms = _extract_entity_terms(blocks)
    assert "冷冻水泵1号" in terms
    assert "CHWP-01" in terms
    assert terms[0] == "冷冻水泵1号"  # 长术语优先


def test_apply_terms_fixes_near_miss_device_name() -> None:
    # 「冷冻水泵1好」→「冷冻水泵1号」
    out = _apply_terms("打开冷冻水泵1好", ["冷冻水泵1号", "CHWP-01"])
    assert out == "打开冷冻水泵1号"


def test_apply_terms_normalizes_device_code_case() -> None:
    out = _apply_terms("查询 chwp-01 状态", ["CHWP-01"])
    assert out == "查询 CHWP-01 状态"


@patch("app.services.voice.semantic.settings")
@patch("app.rag.context.retrieve_entity_blocks")
@patch("app.rag.context.retrieve_knowledge_blocks")
def test_semantic_prefers_entity_over_kb(
    mock_kb,
    mock_entity,
    mock_settings,
) -> None:
    mock_settings.transcribe_rag_enabled = True
    mock_settings.qdrant_url = "http://127.0.0.1:16333"
    mock_settings.transcribe_rag_top_k = 2
    mock_settings.transcribe_correct_min_score = 0.3
    mock_entity.return_value = [
        {
            "title": "冷冻水泵1号",
            "terms": ["冷冻水泵1号", "CHWP-01"],
            "text": "设备名称：冷冻水泵1号",
            "kind": "entity",
        }
    ]
    mock_kb.return_value = [
        {"title": "告警", "text": "告警确认流程"},
    ]
    out = apply_semantic_correction("打开冷冻水泵1好")
    assert out == "打开冷冻水泵1号"
    mock_entity.assert_called_once()
    # 实体已命中则不必再查知识库
    mock_kb.assert_not_called()
