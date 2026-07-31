"""守卫：contracts 不得依赖宿主包名或硬编码兄弟工程路径。"""

from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SCAN_DIR = _ROOT / "contracts"
_IMPORT_RE = re.compile(
    r"^\s*(?:from\s+(?:app|platform_mcp)(?:\.|\s)|import\s+(?:app|platform_mcp)(?:\.|\s|$))",
    re.MULTILINE,
)
# 禁止在生产代码中写死 monorepo 兄弟工程目录名
_SIBLING_PATH_RE = re.compile(r"platform-mcp-server|platform-agent-service")


def test_contracts_have_no_host_package_imports() -> None:
    offenders: list[str] = []
    for path in _SCAN_DIR.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if _IMPORT_RE.search(text):
            offenders.append(f"{path.relative_to(_ROOT)}: import app/platform_mcp")
        if _SIBLING_PATH_RE.search(text):
            offenders.append(f"{path.relative_to(_ROOT)}: sibling path literal")
    assert not offenders, "contracts 边界违规:\n" + "\n".join(offenders)
