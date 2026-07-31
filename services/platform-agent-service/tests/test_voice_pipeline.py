"""多级语音纠错与并行会话单测"""

from __future__ import annotations

from unittest.mock import patch

from app.services.voice.pipeline import multi_stage_correct
from app.services.voice.rules import apply_rule_correction
from app.services.voice.stream_session import StreamSession


class TestRuleCorrection:
    def test_fullwidth_digits(self):
        assert apply_rule_correction("近１２３天") == "近123天"


class TestMultiStagePipeline:
    @patch("app.services.voice.pipeline.settings")
    @patch("app.services.voice.pipeline.cache_get", return_value="打开门禁")
    def test_cache_hit_short_circuits(self, _mock_get, mock_settings):
        mock_settings.transcribe_rag_enabled = True
        mock_settings.transcribe_dictionary_enabled = True
        result = multi_stage_correct("打开门进")
        assert result.text == "打开门禁"
        assert result.stage == "cache"

    @patch("app.services.voice.pipeline.settings")
    @patch("app.services.voice.pipeline.cache_get", return_value=None)
    @patch("app.services.voice.pipeline.cache_set")
    @patch(
        "app.services.voice.pipeline.apply_dictionary_correction",
        return_value="打开门禁",
    )
    def test_dictionary_writes_cache(
        self,
        _mock_dict,
        mock_set,
        _mock_get,
        mock_settings,
    ):
        mock_settings.transcribe_rag_enabled = True
        mock_settings.transcribe_dictionary_enabled = True
        result = multi_stage_correct("打开门进")
        assert result.stage == "dictionary"
        assert result.text == "打开门禁"
        assert mock_set.called


class TestStreamSessionParallel:
    @patch("app.services.transcription.asr_bytes_only", return_value="查告警")
    @patch(
        "app.services.voice.stream_session.multi_stage_correct",
    )
    def test_chunks_submit_without_serial_wait(self, mock_correct, _mock_asr):
        from app.services.voice.types import CorrectResult

        mock_correct.return_value = CorrectResult(
            text="查告警",
            stage="rule",
            changed=False,
            raw="查告警",
        )
        session = StreamSession(session_id="s1", model_id=None)
        # 连续提交，不 await 前一个 future
        r1 = session.submit_chunk(seq=0, audio_bytes=b"aaa", mime="audio/webm")
        r2 = session.submit_chunk(seq=1, audio_bytes=b"bbb", mime="audio/webm")
        assert r1["accepted"] is True
        assert r2["accepted"] is True
        assert r2["pending"] >= 0
        # finalize 收敛
        out = session.finalize(wait_seconds=5)
        assert out["text"] == "查告警"
        assert out["source"] in {"parallel_chunks", "final_full"}
