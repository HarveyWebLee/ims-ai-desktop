"""Realtime ASR 跨 VAD 句累加逻辑。"""

from app.services.voice.realtime_bridge import (
    _display_transcript,
    _join_asr_parts,
    _preview_text,
)


def test_preview_text_concat_text_and_stash() -> None:
    assert _preview_text({"text": "查询", "stash": "近三天"}) == "查询近三天"
    assert _preview_text({"text": "", "stash": "今天"}) == "今天"
    assert _preview_text({"text": "今天天气不错，", "stash": ""}) == "今天天气不错，"


def test_join_asr_parts_no_space() -> None:
    assert _join_asr_parts("查询近三天", "门禁报警") == "查询近三天门禁报警"
    assert _join_asr_parts("", "仅当前") == "仅当前"
    assert _join_asr_parts("已有", "", "后续") == "已有后续"


def test_display_transcript_accumulates_turns() -> None:
    committed = ["查询近三天的", "门禁记录"]
    assert _display_transcript(committed) == "查询近三天的门禁记录"
    assert _display_transcript(committed, "并导出") == "查询近三天的门禁记录并导出"


def test_new_turn_preview_does_not_drop_committed() -> None:
    """模拟：第一句 completed 后，第二句 partial 从空开始。"""
    committed = ["打开设备管理"]
    # 新 item 的 text+stash 只有后半句
    preview = _preview_text({"text": "", "stash": "页面"})
    assert _display_transcript(committed, preview) == "打开设备管理页面"
