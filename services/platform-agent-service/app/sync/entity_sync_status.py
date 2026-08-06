"""实体同步最近一次结果与水位线（内存 + 可选 Agent Postgres；禁达梦写标记）。"""

from __future__ import annotations

from typing import Any

from app.infrastructure.persistence.entity_sync_repository import (
    clear_entity_sync_persistence,
    configure_entity_sync_persistence,
    get_entity_sync_snapshot,
    list_entity_sync_checkpoints,
    remember_entity_sync_result,
    upsert_entity_sync_checkpoint,
)


def get_entity_sync_status() -> dict[str, Any]:
    """返回最近一次结果、水位线与是否进行中；无记录时 result=null。"""
    return get_entity_sync_snapshot()


def clear_entity_sync_status(*, clear_db: bool = False) -> None:
    """测试用。"""
    clear_entity_sync_persistence(clear_db=clear_db)


def table_to_stream_name(table_name: str) -> str:
    """表名 → checkpoint stream（与架构文档 device|variable 对齐）。"""
    name = (table_name or "").strip().lower()
    if name == "p_device":
        return "device"
    if name == "p_device_variable":
        return "variable"
    return name or "unknown"


__all__ = [
    "clear_entity_sync_status",
    "configure_entity_sync_persistence",
    "get_entity_sync_status",
    "list_entity_sync_checkpoints",
    "remember_entity_sync_result",
    "table_to_stream_name",
    "upsert_entity_sync_checkpoint",
]
