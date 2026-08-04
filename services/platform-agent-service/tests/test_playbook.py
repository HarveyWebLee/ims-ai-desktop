"""运行时 Playbook：加载、匹配与注入格式。"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from pathlib import Path

import pytest

from app.services.playbook.loader import load_playbooks_from_dir, parse_playbook_markdown
from app.services.playbook.service import (
    clear_playbook_cache,
    format_playbook_section,
    match_playbooks,
)


@pytest.fixture(autouse=True)
def _clear_cache() -> Iterator[None]:
    clear_playbook_cache()
    yield
    clear_playbook_cache()


def test_parse_playbook_frontmatter() -> None:
    text = """---
id: demo
title: 演示
version: "1.2"
priority: 7
triggers:
  - 告警
  - 处理告警
domains:
  - alarm
---

## 步骤

1. 查询
"""
    pb = parse_playbook_markdown(text)
    assert pb is not None
    assert pb.id == "demo"
    assert pb.title == "演示"
    assert pb.version == "1.2"
    assert pb.priority == 7
    assert pb.triggers == ("告警", "处理告警")
    assert pb.domains == ("alarm",)
    assert "查询" in pb.body


def test_builtin_playbooks_load() -> None:
    from app.services.playbook.loader import default_playbooks_dir

    loaded = load_playbooks_from_dir(default_playbooks_dir())
    ids = {p.id for p in loaded}
    assert "alarm-dispose" in ids
    assert "batch-export" in ids


def test_match_alarm_dispose(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "agent_playbook_enabled", True)
    monkeypatch.setattr(settings, "agent_playbook_dir", "")
    monkeypatch.setattr(settings, "agent_playbook_max_matches", 2)
    clear_playbook_cache()

    matches = match_playbooks("帮我处理未确认告警")
    assert matches
    assert matches[0].playbook.id == "alarm-dispose"
    section = format_playbook_section(matches)
    assert "场景 Playbook" in section
    assert "alarm-dispose" in section


def test_match_batch_export_over_alarm(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "agent_playbook_enabled", True)
    monkeypatch.setattr(settings, "agent_playbook_dir", "")
    monkeypatch.setattr(settings, "agent_playbook_max_matches", 1)
    clear_playbook_cache()

    matches = match_playbooks("导出今天的告警 excel")
    assert len(matches) == 1
    assert matches[0].playbook.id == "batch-export"


def test_howto_export_skips_playbook(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "agent_playbook_enabled", True)
    monkeypatch.setattr(settings, "agent_playbook_dir", "")
    monkeypatch.setattr(settings, "agent_playbook_max_matches", 2)
    clear_playbook_cache()

    assert match_playbooks("怎么导出告警报表？需要注意什么？") == []
    assert match_playbooks("如何导出告警报表") == []


def test_playbook_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "agent_playbook_enabled", False)
    assert match_playbooks("处理告警") == []


def test_assemble_context_injects_playbook(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import settings
    from app.graph.context import assemble_context

    monkeypatch.setattr(settings, "agent_playbook_enabled", True)
    monkeypatch.setattr(settings, "agent_playbook_dir", "")
    monkeypatch.setattr(settings, "agent_playbook_max_matches", 2)
    # 跳过被动 RAG（无 Qdrant 也能测 playbook）
    monkeypatch.setattr(settings, "qdrant_url", "")
    clear_playbook_cache()

    from app.services.prompt_assembly import extract_user_display_message

    ctx = assemble_context(thread_id="t-pb", message="请确认未处理告警")
    assert "场景 Playbook" in ctx.llm_user_message
    assert "alarm-dispose" in ctx.llm_user_message
    assert "请确认未处理告警" in ctx.llm_user_message
    # 历史回显须剥离 Playbook，只保留用户原话
    assert extract_user_display_message(ctx.llm_user_message) == "请确认未处理告警"


def test_assemble_context_howto_export_no_playbook(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import settings
    from app.graph.context import assemble_context
    from app.services.prompt_assembly import extract_user_display_message

    monkeypatch.setattr(settings, "agent_playbook_enabled", True)
    monkeypatch.setattr(settings, "agent_playbook_dir", "")
    monkeypatch.setattr(settings, "agent_playbook_max_matches", 2)
    monkeypatch.setattr(settings, "qdrant_url", "")
    clear_playbook_cache()

    msg = "怎么导出告警报表？需要注意什么？"
    ctx = assemble_context(thread_id="t-howto", message=msg)
    assert "场景 Playbook" not in ctx.llm_user_message
    assert "batch-export" not in ctx.llm_user_message
    assert "操作说明" in ctx.llm_user_message or "注意事项" in ctx.llm_user_message
    assert "download_file" in ctx.llm_user_message  # 注记中禁止调用
    assert extract_user_display_message(ctx.llm_user_message) == msg


def test_custom_playbook_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from app.config import settings

    custom = tmp_path / "pb"
    custom.mkdir()
    (custom / "custom.md").write_text(
        """---
id: custom-only
title: 自定义
version: "0.1"
priority: 1
triggers:
  - 自定义流程词
---

仅自定义正文
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(settings, "agent_playbook_enabled", True)
    monkeypatch.setattr(settings, "agent_playbook_dir", str(custom))
    monkeypatch.setattr(settings, "agent_playbook_max_matches", 1)
    clear_playbook_cache()

    matches = match_playbooks("走自定义流程词")
    assert len(matches) == 1
    assert matches[0].playbook.id == "custom-only"


def test_is_playbook_file() -> None:
    from app.services.playbook.watcher import is_playbook_file

    assert is_playbook_file("/x/alarm-dispose.md")
    assert is_playbook_file("BATCH-EXPORT.MD")
    assert not is_playbook_file("/x/README.txt")
    assert not is_playbook_file("/x/.hidden.md")


@pytest.mark.asyncio
async def test_playbook_watcher_reloads_on_change(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from app.config import settings
    from app.services.playbook.service import list_playbooks, reload_playbooks
    from app.services.playbook.watcher import _watch_loop

    custom = tmp_path / "pb"
    custom.mkdir()
    target = custom / "hot.md"
    target.write_text(
        """---
id: hot-v1
title: 热更前
version: "1"
priority: 1
triggers:
  - 热更探针词
---

版本一
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(settings, "agent_playbook_enabled", True)
    monkeypatch.setattr(settings, "agent_playbook_watch", True)
    monkeypatch.setattr(settings, "agent_playbook_dir", str(custom))
    monkeypatch.setattr(settings, "agent_playbook_max_matches", 1)
    clear_playbook_cache()
    assert reload_playbooks()[0].id == "hot-v1"

    stop = asyncio.Event()

    async def writer() -> None:
        await asyncio.sleep(0.6)
        target.write_text(
            """---
id: hot-v2
title: 热更后
version: "2"
priority: 1
triggers:
  - 热更探针词
---

版本二
""",
            encoding="utf-8",
        )
        for _ in range(40):
            await asyncio.sleep(0.15)
            if [p.id for p in list_playbooks()] == ["hot-v2"]:
                break
        stop.set()

    await asyncio.wait_for(
        asyncio.gather(_watch_loop(custom, stop), writer()),
        timeout=12,
    )
    assert [p.id for p in list_playbooks()] == ["hot-v2"]


@pytest.mark.asyncio
async def test_start_playbook_watcher_respects_flags(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.config import settings
    from app.services.playbook.watcher import start_playbook_watcher, stop_playbook_watcher

    monkeypatch.setattr(settings, "agent_playbook_enabled", False)
    monkeypatch.setattr(settings, "agent_playbook_watch", True)
    assert await start_playbook_watcher() is False
    monkeypatch.setattr(settings, "agent_playbook_enabled", True)
    monkeypatch.setattr(settings, "agent_playbook_watch", False)
    assert await start_playbook_watcher() is False
    await stop_playbook_watcher()
