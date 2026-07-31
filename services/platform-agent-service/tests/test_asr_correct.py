"""语音转写后纠错入口单测（委托 multi_stage_correct）"""

from __future__ import annotations

from unittest.mock import patch

from app.services.asr_correct import correct_asr_transcript
from app.services.voice.types import CorrectResult


@patch("app.services.asr_correct.multi_stage_correct")
def test_correct_delegates(mock_pipeline):
    mock_pipeline.return_value = CorrectResult(
        text="打开门禁",
        stage="dictionary",
        changed=True,
        raw="打开门进",
    )
    assert correct_asr_transcript("打开门进") == "打开门禁"
    mock_pipeline.assert_called_once_with("打开门进")
