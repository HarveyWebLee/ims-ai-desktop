"""Stage 1：规则纠错（全角数字、空白、NFKC 等，毫秒级）。"""

from __future__ import annotations

import re
import unicodedata

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
_MULTI_PUNCT_RE = re.compile(r"[，,]{2,}")


def apply_rule_correction(text: str) -> str:
    """确定性规则规范化；不写 Cache。"""
    raw = text or ""
    out = unicodedata.normalize("NFKC", raw)
    out = out.translate(_FULLWIDTH_DIGIT_TRANS)
    out = _MULTI_SPACE_RE.sub(" ", out)
    out = _MULTI_PUNCT_RE.sub("，", out)
    return out.strip()
