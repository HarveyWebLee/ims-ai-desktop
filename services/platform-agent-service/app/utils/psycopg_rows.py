"""psycopg 查询行类型辅助（bootstrap 使用 dict_row 工厂）。"""

from __future__ import annotations

from typing import Any, cast


def as_dict_row(row: object) -> dict[str, Any]:
    """将 psycopg 行对象收窄为 dict[str, Any]（运行时由 dict_row 保证）。"""
    return cast(dict[str, Any], row)
