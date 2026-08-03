"""Stage 1：规则纠错（全角数字、空白等，毫秒级）。

不改动原有标点的中/英形态（交由 LLM 按句类与语境处理句末语气标点）。
"""

from __future__ import annotations

import re

_FULLWIDTH_DIGIT_TRANS = str.maketrans(
    {
        "０": "0",
        "１": "1",
        "２": "2",
        "３": "3",
        "４": "4",
        "５": "5",
        "６": "6",
        "７": "7",
        "８": "8",
        "９": "9",
    }
)
_MULTI_SPACE_RE = re.compile(r"[ \t\u3000]+")
_MULTI_COMMA_RE = re.compile(r"[，,]{2,}")


def _collapse_duplicate_commas(text: str) -> str:
    """连续逗号压成一个，保留原文中/英形态（含中文则留中文）。"""

    def _repl(match: re.Match[str]) -> str:
        chunk = match.group(0)
        return "，" if "，" in chunk else ","

    return _MULTI_COMMA_RE.sub(_repl, text)


def apply_rule_correction(text: str) -> str:
    """确定性规则规范化；不写 Cache；不改标点中英形态。"""
    raw = text or ""
    # 仅转全角数字，避免 NFKC 改写标点
    out = raw.translate(_FULLWIDTH_DIGIT_TRANS)
    out = _MULTI_SPACE_RE.sub(" ", out)
    out = _collapse_duplicate_commas(out)
    return out.strip()
