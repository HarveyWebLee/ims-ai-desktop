"""多级纠错结果类型。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CorrectResult:
    """纠错输出。"""

    text: str
    stage: str
    changed: bool
    raw: str
