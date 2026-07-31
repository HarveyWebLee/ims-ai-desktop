"""守卫：Agent 生产代码与测试不得 import platform_mcp 包。"""

from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SCAN_DIRS = (_ROOT / "app", _ROOT / "tests")
_IMPORT_RE = re.compile(
    r"^\s*(?:from\s+platform_mcp(?:\.|\s)|import\s+platform_mcp(?:\.|\s|$))",
    re.MULTILINE,
)
_SELF = Path(__file__).name


def test_app_and_tests_have_no_platform_mcp_imports() -> None:
    offenders: list[str] = []
    for base in _SCAN_DIRS:
        for path in base.rglob("*.py"):
            if path.name == _SELF:
                continue
            text = path.read_text(encoding="utf-8")
            if _IMPORT_RE.search(text):
                offenders.append(str(path.relative_to(_ROOT)))
    assert not offenders, "Agent 禁止 import platform_mcp:\n" + "\n".join(offenders)
