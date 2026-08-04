"""实体同步最近一次结果（进程内，供运营可观测）。"""

from __future__ import annotations

import threading
from datetime import UTC, datetime
from typing import Any

_lock = threading.Lock()
_last_at: str | None = None
_last_result: dict[str, Any] | None = None


def remember_entity_sync_result(result: dict[str, Any]) -> None:
    """记录最近一次同步返回（含 skipped / 失败）。"""
    global _last_at, _last_result
    with _lock:
        _last_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        _last_result = dict(result)


def get_entity_sync_status() -> dict[str, Any]:
    """返回最近一次结果；无记录时 result=null。"""
    from app.sync.entity_sync_service import is_entity_sync_running

    with _lock:
        return {
            "in_progress": is_entity_sync_running(),
            "at": _last_at,
            "result": dict(_last_result) if _last_result is not None else None,
        }


def clear_entity_sync_status() -> None:
    """测试用。"""
    global _last_at, _last_result
    with _lock:
        _last_at = None
        _last_result = None
