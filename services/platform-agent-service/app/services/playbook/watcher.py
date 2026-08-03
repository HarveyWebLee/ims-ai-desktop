"""Playbook 目录监听：.md 变更时 reload 内存缓存（不重启 Agent 进程）。"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_task: asyncio.Task[None] | None = None
_stop_event: asyncio.Event | None = None


def is_playbook_file(path: str) -> bool:
    """仅关心 Markdown 剧本文件。"""
    name = Path(path).name
    if name.startswith("."):
        return False
    return name.lower().endswith(".md")


async def _watch_loop(directory: Path, stop_event: asyncio.Event) -> None:
    from watchfiles import Change, awatch

    from app.services.playbook.service import reload_playbooks

    def _filter(change: Change, path: str) -> bool:  # noqa: ARG001
        return is_playbook_file(path)

    logger.info("playbook watcher started: dir=%s", directory)
    try:
        async for changes in awatch(
            str(directory),
            watch_filter=_filter,
            stop_event=stop_event,
            debounce=400,
            recursive=False,
            # Windows 下原生 notify 偶发漏事件；轮询对小目录成本可忽略
            force_polling=True,
            poll_delay_ms=300,
        ):
            if stop_event.is_set():
                break
            changed = sorted({Path(p).name for _, p in changes})
            try:
                loaded = reload_playbooks()
                logger.info(
                    "playbook hot-reload ok: count=%s changed=%s",
                    len(loaded),
                    changed,
                )
            except Exception:  # noqa: BLE001
                logger.exception("playbook hot-reload failed: changed=%s", changed)
    except asyncio.CancelledError:
        raise
    except Exception:  # noqa: BLE001
        logger.exception("playbook watcher stopped unexpectedly")
    finally:
        logger.info("playbook watcher stopped: dir=%s", directory)


async def start_playbook_watcher() -> bool:
    """启动目录监听；成功返回 True，跳过/失败返回 False。"""
    global _task, _stop_event

    from app.config import settings
    from app.services.playbook.service import resolve_playbooks_dir

    if _task is not None and not _task.done():
        return True
    if not settings.agent_playbook_enabled or not settings.agent_playbook_watch:
        return False

    directory = resolve_playbooks_dir()
    if not directory.is_dir():
        logger.warning("playbook watcher skipped: dir missing %s", directory)
        return False

    _stop_event = asyncio.Event()
    _task = asyncio.create_task(
        _watch_loop(directory, _stop_event),
        name="playbook-watcher",
    )
    return True


async def stop_playbook_watcher() -> None:
    """停止监听任务。"""
    global _task, _stop_event

    stop = _stop_event
    task = _task
    _stop_event = None
    _task = None
    if stop is not None:
        stop.set()
    if task is None:
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
