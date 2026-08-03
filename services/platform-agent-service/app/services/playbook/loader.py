"""Playbook Markdown 加载与简易 frontmatter 解析（无额外 YAML 依赖）。"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

_FRONTMATTER_RE = re.compile(
    r"\A---\s*\n(?P<meta>.*?)\n---\s*\n(?P<body>.*)\Z",
    re.DOTALL,
)


@dataclass(frozen=True)
class Playbook:
    """单份可版本化场景规程。"""

    id: str
    title: str
    version: str
    body: str
    triggers: tuple[str, ...] = ()
    domains: tuple[str, ...] = ()
    priority: int = 0
    source_path: str = ""


def default_playbooks_dir() -> Path:
    """内置 playbooks 目录：app/playbooks。"""
    return Path(__file__).resolve().parents[2] / "playbooks"


def _parse_scalar(raw: str) -> str | int:
    text = raw.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
        return text[1:-1]
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    return text


def _parse_frontmatter(meta: str) -> dict[str, object]:
    """
    解析受限 frontmatter：标量 + 缩进列表。

    仅支持本仓 playbook 所需键，避免引入 PyYAML。
    """
    result: dict[str, object] = {}
    current_list_key: str | None = None
    current_list: list[str] = []

    def flush_list() -> None:
        nonlocal current_list_key, current_list
        if current_list_key is not None:
            result[current_list_key] = list(current_list)
            current_list_key = None
            current_list = []

    for line in meta.splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        list_item = re.match(r"^(\s+)-\s+(.*)$", line)
        if list_item and current_list_key is not None:
            current_list.append(str(_parse_scalar(list_item.group(2))))
            continue
        kv = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", line)
        if not kv:
            continue
        flush_list()
        key, value = kv.group(1), kv.group(2)
        if value == "":
            current_list_key = key
            current_list = []
            continue
        result[key] = _parse_scalar(value)
    flush_list()
    return result


def parse_playbook_markdown(text: str, *, source_path: str = "") -> Playbook | None:
    """解析单文件；缺 id 或正文为空则返回 None。"""
    raw = text.strip()
    if not raw:
        return None
    match = _FRONTMATTER_RE.match(raw)
    if not match:
        logger.warning("playbook missing frontmatter: %s", source_path or "<memory>")
        return None
    meta = _parse_frontmatter(match.group("meta"))
    body = (match.group("body") or "").strip()
    playbook_id = str(meta.get("id") or "").strip()
    if not playbook_id or not body:
        logger.warning("playbook missing id/body: %s", source_path or "<memory>")
        return None
    triggers_raw = meta.get("triggers") or []
    domains_raw = meta.get("domains") or []
    triggers = tuple(
        str(t).strip()
        for t in (triggers_raw if isinstance(triggers_raw, list) else [])
        if str(t).strip()
    )
    domains = tuple(
        str(d).strip()
        for d in (domains_raw if isinstance(domains_raw, list) else [])
        if str(d).strip()
    )
    priority_val = meta.get("priority", 0)
    try:
        priority = int(priority_val)  # type: ignore[arg-type]
    except TypeError, ValueError:
        priority = 0
    return Playbook(
        id=playbook_id,
        title=str(meta.get("title") or playbook_id).strip(),
        version=str(meta.get("version") or "0").strip(),
        body=body,
        triggers=triggers,
        domains=domains,
        priority=priority,
        source_path=source_path,
    )


def load_playbooks_from_dir(directory: Path) -> list[Playbook]:
    """加载目录下全部 .md（跳过 README.md）。"""
    if not directory.is_dir():
        logger.warning("playbook dir missing: %s", directory)
        return []
    loaded: list[Playbook] = []
    for path in sorted(directory.glob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            logger.exception("failed reading playbook %s", path)
            continue
        pb = parse_playbook_markdown(text, source_path=str(path))
        if pb:
            loaded.append(pb)
    return loaded
