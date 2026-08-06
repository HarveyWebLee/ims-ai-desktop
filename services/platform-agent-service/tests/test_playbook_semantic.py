"""Playbook 语义召回并集（mock，不依赖 Qdrant）。"""

from __future__ import annotations

from app.services.playbook.service import clear_playbook_cache, match_playbooks


def test_semantic_bonus_can_surface_playbook(monkeypatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "agent_playbook_enabled", True)
    monkeypatch.setattr(settings, "agent_playbook_dir", "")
    monkeypatch.setattr(settings, "agent_playbook_max_matches", 2)
    monkeypatch.setattr(settings, "agent_playbook_semantic_enabled", True)
    clear_playbook_cache()

    def _fake_semantic(query: str, *, limit: int | None = None):  # noqa: ARG001
        return [("alarm-dispose", 0.82)]

    monkeypatch.setattr(
        "app.services.playbook.semantic.semantic_search_playbook_ids",
        _fake_semantic,
    )

    # 无「告警」等强触发词时，靠语义抬出 alarm-dispose
    matches = match_playbooks("请按规程处置一下异常事件")
    ids = [m.playbook.id for m in matches]
    assert "alarm-dispose" in ids


def test_semantic_disabled_keeps_keyword_path(monkeypatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "agent_playbook_enabled", True)
    monkeypatch.setattr(settings, "agent_playbook_dir", "")
    monkeypatch.setattr(settings, "agent_playbook_semantic_enabled", False)
    clear_playbook_cache()

    matches = match_playbooks("帮我处理未确认告警")
    assert matches
    assert matches[0].playbook.id == "alarm-dispose"


def test_playbook_index_text_contains_title() -> None:
    from app.services.playbook.loader import default_playbooks_dir, load_playbooks_from_dir
    from app.services.playbook.semantic import playbook_index_text

    loaded = load_playbooks_from_dir(default_playbooks_dir())
    alarm = next(p for p in loaded if p.id == "alarm-dispose")
    text = playbook_index_text(alarm)
    assert "告警处置" in text
    assert "alarm-dispose" in text
