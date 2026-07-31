"""解析 ENTITY_SYNC_TABLES 配置。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TableSyncPlan:
    """同步计划：是否跳过、是否全部表、显式表名列表。"""

    skip: bool
    all_tables: bool
    explicit_tables: tuple[str, ...]


def parse_entity_sync_tables(raw: str | None) -> TableSyncPlan:
    """
    解析表同步配置。

    - 空 / 仅空白 → skip（不转换）
    - ``*`` → 全部表
    - ``a,b,c`` → 显式列表（去空白、去空段、保序去重，小写）
    """
    text = (raw or "").strip()
    if not text:
        return TableSyncPlan(skip=True, all_tables=False, explicit_tables=())
    if text == "*":
        return TableSyncPlan(skip=False, all_tables=True, explicit_tables=())

    seen: set[str] = set()
    ordered: list[str] = []
    for part in text.split(","):
        name = part.strip().lower()
        if not name or name in seen:
            continue
        seen.add(name)
        ordered.append(name)
    if not ordered:
        return TableSyncPlan(skip=True, all_tables=False, explicit_tables=())
    return TableSyncPlan(skip=False, all_tables=False, explicit_tables=tuple(ordered))
