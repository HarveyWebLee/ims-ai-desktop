"""
知识库 source / doc_id 规范化。

- ``source``：入库主键展示值，统一为 resolve 后的绝对路径（POSIX 分隔符）。
- ``doc_id``：跨路径写法的稳定文档键；在文档目录内用相对路径，否则用绝对路径哈希。
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path


def normalize_source(value: str | Path | None) -> str:
    """
    规范化 source 字符串。

    - 去首尾空白；空串保持空
    - 绝对路径或磁盘上存在的路径：resolve 为绝对路径，分隔符统一 ``/``
    - 其它逻辑键（如 ``ops.md``）：仅将 ``\\`` 转为 ``/``，不擅自 resolve
    """
    if value is None:
        return ""
    raw = str(value).strip()
    if not raw:
        return ""
    path = Path(raw)
    if path.is_absolute() or path.exists():
        try:
            return path.expanduser().resolve().as_posix()
        except OSError:
            return raw.replace("\\", "/")
    return raw.replace("\\", "/")


def compute_doc_id(
    source: str | Path | None,
    *,
    docs_root: Path | str | None = None,
) -> str:
    """
    由 source 计算稳定 ``doc_id``。

    - 若 ``docs_root`` 给定且 source 落在其下：返回相对路径（POSIX；Windows 下小写）
    - 否则：``abs:`` + sha256(规范化绝对路径) 前 32 hex
    """
    src = normalize_source(source)
    if not src:
        return ""

    if docs_root is not None:
        try:
            root = Path(docs_root).expanduser().resolve()
            rel = Path(src).resolve().relative_to(root)
            key = rel.as_posix()
            if os.name == "nt":
                key = key.lower()
            return key
        except OSError, ValueError:
            pass

    digest = hashlib.sha256(src.encode("utf-8")).hexdigest()[:32]
    return f"abs:{digest}"


def source_lookup_candidates(value: str | Path | None) -> list[str]:
    """
    删除/匹配时尝试的 source 变体（规范化 + 原始 strip），去重保序。
    """
    raw = str(value or "").strip()
    normalized = normalize_source(value)
    out: list[str] = []
    for item in (normalized, raw, raw.replace("\\", "/"), raw.replace("/", "\\")):
        if item and item not in out:
            out.append(item)
    return out
