"""将 Agent 宿主能力注入 ``contracts`` 运行时钩子（单向依赖）。

须在进程启动早期调用（``app.config`` 导入后 / FastAPI lifespan 前），
保证 preflight 会话回填、共享 JSON 路径与 AgentTrace 编排快照可用。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

_wired = False
_SERVICE_ROOT = Path(__file__).resolve().parent.parent
_APP_DATA = _SERVICE_ROOT / "app" / "data"
_TOOL_CATALOG = _SERVICE_ROOT / "app" / "tools" / "catalog.json"


def wire_contracts_runtime(*, force: bool = False) -> None:
    """绑定 settings / 共享 data 目录 / 会话历史 / 编排探针。幂等。"""
    global _wired
    if _wired and not force:
        return

    from app.config import settings
    from app.services.bpmn_execution_state import get_bpmn_execution_state
    from app.services.session_store import get_thread_bpmn_snapshot, session_store
    from contracts.runtime_bind import (
        bind_orchestration_probe,
        bind_prior_user_messages,
        bind_settings,
        bind_shared_data_dir,
    )

    def _prior_user_messages(thread_id: str, limit: int) -> list[str]:
        return session_store.get_user_messages(thread_id, limit=limit)

    def _orchestration_probe(thread_id: str) -> dict[str, Any]:
        tid = (thread_id or "").strip()
        snap: dict[str, Any] = {"thread_id": tid}
        try:
            snap["has_bpmn_snapshot"] = get_thread_bpmn_snapshot(tid) is not None
        except Exception:  # noqa: BLE001
            snap["has_bpmn_snapshot"] = False
        try:
            snap["has_execution_state"] = get_bpmn_execution_state(tid) is not None
        except Exception:  # noqa: BLE001
            snap["has_execution_state"] = False
        return snap

    # Agent 权威：app/data（navigation / device_action / platform_api_*）
    bind_shared_data_dir(_APP_DATA)
    os.environ.setdefault("AGENT_CATALOG_PATH", str(_TOOL_CATALOG.resolve()))
    os.environ.setdefault("AGENT_DATA_DIR", str(_APP_DATA.resolve()))

    bind_settings(settings)
    bind_prior_user_messages(_prior_user_messages)
    bind_orchestration_probe(_orchestration_probe)
    _wired = True
