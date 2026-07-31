"""进程侧运行时注入：由 Agent / MCP 启动时绑定，避免 contracts 反向依赖宿主包。

边界
----
``contracts`` 不得 ``import app`` / ``import platform_mcp``，
也不得硬编码 monorepo 内其他服务工程的目录路径。
需要宿主能力时经本模块注册。
"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

# Agent / MCP 启动时绑定的配置对象（与各自 settings 单例同一引用，便于 monkeypatch）
_settings_source: Any | None = None

# catalog / navigation / device_action 等共享 JSON 目录
_shared_data_dir: Path | None = None

# (thread_id, limit) → 近期用户消息；未绑定时 enrich 不读会话历史
PriorUserMessagesFn = Callable[[str, int], list[str]]
_prior_user_messages_fn: PriorUserMessagesFn | None = None

# thread_id → 编排调试快照字段；未绑定时仅返回 thread_id + 假阴性标志
OrchestrationProbeFn = Callable[[str], dict[str, Any]]
_orchestration_probe_fn: OrchestrationProbeFn | None = None

# 包内默认 data（无兄弟工程名）；宿主应 bind 或设 PLATFORM_MCP_DATA_DIR
_CONTRACTS_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_SHARED_DATA = _CONTRACTS_ROOT / "data"


def bind_settings(source: Any | None) -> None:
    """绑定宿主 settings 单例；传 None 解除绑定。"""
    global _settings_source
    _settings_source = source


def get_bound_settings() -> Any | None:
    """当前绑定的宿主 settings；未绑定返回 None。"""
    return _settings_source


def bind_shared_data_dir(path: str | Path | None) -> None:
    """绑定共享 JSON 数据目录（catalog / navigation / device_action）。"""
    global _shared_data_dir
    if path is None or str(path).strip() == "":
        _shared_data_dir = None
        return
    _shared_data_dir = Path(path).expanduser().resolve()


def resolve_shared_data_dir() -> Path:
    """解析共享数据目录：环境变量 > bind > 包内 ``data/``。"""
    override = (
        os.environ.get("PLATFORM_MCP_DATA_DIR") or os.environ.get("CONTRACTS_DATA_DIR") or ""
    ).strip()
    if override:
        data_dir = Path(override).expanduser().resolve()
    elif _shared_data_dir is not None:
        data_dir = _shared_data_dir
    else:
        data_dir = _DEFAULT_SHARED_DATA
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def bind_prior_user_messages(fn: PriorUserMessagesFn | None) -> None:
    """绑定「按 thread 取近期用户消息」；MCP 进程通常不绑。"""
    global _prior_user_messages_fn
    _prior_user_messages_fn = fn


def lookup_prior_user_messages(thread_id: str, *, limit: int = 1) -> list[str]:
    """经钩子读取近期用户消息；未绑定或失败时返回空列表。"""
    fn = _prior_user_messages_fn
    if fn is None:
        return []
    tid = (thread_id or "").strip()
    if not tid:
        return []
    try:
        return list(fn(tid, limit))
    except Exception:  # noqa: BLE001 — 钩子失败时降级，不阻断 preflight
        return []


def bind_orchestration_probe(fn: OrchestrationProbeFn | None) -> None:
    """绑定编排调试探针（BPMN / execution_state 等）；仅 Agent 需要。"""
    global _orchestration_probe_fn
    _orchestration_probe_fn = fn


def run_orchestration_probe(thread_id: str) -> dict[str, Any] | None:
    """执行已绑定探针；未绑定返回 None。"""
    fn = _orchestration_probe_fn
    if fn is None:
        return None
    return fn((thread_id or "").strip())
