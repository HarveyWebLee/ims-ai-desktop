"""Stage 3：项目术语词典纠错（很低耗时）。"""

from __future__ import annotations

import json
import logging
import re
from functools import lru_cache
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

_DEFAULT_DICT = Path(__file__).resolve().parent.parent.parent / "data" / "asr_dictionary.json"


@lru_cache(maxsize=1)
def _load_entries() -> list[tuple[str, str]]:
    path = (settings.transcribe_dictionary_path or "").strip()
    file_path = Path(path) if path else _DEFAULT_DICT
    if not file_path.is_file():
        logger.warning("asr dictionary missing: %s", file_path)
        return []
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("asr dictionary load failed: %s", exc)
        return []
    entries: list[tuple[str, str]] = []
    for item in payload.get("entries") or []:
        if not isinstance(item, dict):
            continue
        src = str(item.get("from") or "").strip()
        dst = str(item.get("to") or "").strip()
        if not src or not dst or src == dst:
            continue
        entries.append((src, dst))
    # 长词优先，避免短词抢先替换
    entries.sort(key=lambda pair: len(pair[0]), reverse=True)
    return entries


def apply_dictionary_correction(text: str) -> str:
    """按词典替换；大小写不敏感匹配英文别名。"""
    out = text or ""
    if not out:
        return out
    for src, dst in _load_entries():
        if not src:
            continue
        if re.search(r"[A-Za-z]", src):
            pattern = re.compile(re.escape(src), re.IGNORECASE)
            out = pattern.sub(dst, out)
        elif src in out:
            out = out.replace(src, dst)
    return out
