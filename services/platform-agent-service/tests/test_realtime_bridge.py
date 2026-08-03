"""Realtime ASR 按段协议辅助函数。"""

from app.services.voice.realtime_bridge import (
    _committed_text,
    _join_asr_parts,
    _preview_text,
    _prior_context,
    _segment_payload,
    _segments_snapshot,
)


def test_preview_text_concat_text_and_stash() -> None:
    assert _preview_text({"text": "查询", "stash": "近三天"}) == "查询近三天"
    assert _preview_text({"text": "", "stash": "今天"}) == "今天"
    assert _preview_text({"text": "今天天气不错，", "stash": ""}) == "今天天气不错，"


def test_join_asr_parts_no_space() -> None:
    assert _join_asr_parts("查询近三天", "门禁报警") == "查询近三天门禁报警"
    assert _join_asr_parts("", "仅当前") == "仅当前"
    assert _join_asr_parts("已有", "", "后续") == "已有后续"


def test_committed_text_uses_corrected_segment_text() -> None:
    segments = [
        {"seq": 0, "text": "打开冷冻水泵"},
        {"seq": 1, "text": "并导出"},
    ]
    assert _committed_text(segments) == "打开冷冻水泵并导出"


def test_prior_context_excludes_current_seq() -> None:
    segments = [
        {"seq": 0, "text": "打开设备"},
        {"seq": 1, "text": "管理页面"},
        {"seq": 2, "text": "查询报警"},
    ]
    assert _prior_context(segments, 2) == "打开设备管理页面"
    assert _prior_context(segments, 0) == ""


def test_segment_payload_and_snapshot() -> None:
    pending = _segment_payload(
        seq=0,
        raw="冷动水泵",
        text="冷动水泵",
        status="pending",
    )
    assert pending["type"] == "segment"
    assert pending["status"] == "pending"
    assert "stage" not in pending

    done = _segment_payload(
        seq=0,
        raw="冷动水泵",
        text="冷冻水泵",
        status="done",
        changed=True,
        stage="dictionary",
    )
    snap = _segments_snapshot(
        [
            {
                "seq": 0,
                "raw": done["raw"],
                "text": done["text"],
                "stage": done["stage"],
                "changed": True,
                "status": "done",
            }
        ]
    )
    assert snap == [
        {
            "seq": 0,
            "raw": "冷动水泵",
            "text": "冷冻水泵",
            "stage": "dictionary",
            "changed": True,
            "status": "done",
        }
    ]
