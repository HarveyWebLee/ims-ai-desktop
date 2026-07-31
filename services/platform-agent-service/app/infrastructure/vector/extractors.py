"""
多格式知识文件 → 纯文本抽取。

支持任意目录递归：文档 / 表格 / 图片（VL）等。
旧版二进制 Office（.doc / .ppt）需先转为新格式。
"""

from __future__ import annotations

import csv
import html
import logging
import re
from collections.abc import Callable
from io import StringIO
from pathlib import Path

logger = logging.getLogger(__name__)

STRUCTURED_SUFFIXES: frozenset[str] = frozenset(
    {
        ".docx",
        ".pptx",
        ".pdf",
        ".xlsx",
        ".xls",
        ".html",
        ".htm",
        ".csv",
        ".tsv",
    }
)

IMAGE_SUFFIXES: frozenset[str] = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".bmp",
    }
)

TEXT_SUFFIXES: frozenset[str] = frozenset(
    {
        ".md",
        ".markdown",
        ".txt",
        ".rst",
        ".mdc",
        ".log",
        ".json",
        ".jsonl",
        ".yaml",
        ".yml",
        ".xml",
        ".toml",
        ".ini",
        ".cfg",
        ".conf",
        ".py",
        ".pyi",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".java",
        ".go",
        ".rs",
        ".sql",
        ".sh",
        ".bat",
        ".ps1",
        ".css",
        ".scss",
        ".less",
        ".vue",
        ".svelte",
    }
)

UNSUPPORTED_BINARY_SUFFIXES: frozenset[str] = frozenset(
    {
        ".doc",
        ".ppt",
        ".exe",
        ".dll",
        ".so",
        ".dylib",
        ".zip",
        ".rar",
        ".7z",
        ".gz",
        ".tar",
        ".ico",
        ".mp3",
        ".mp4",
        ".wav",
        ".avi",
        ".mov",
        ".woff",
        ".woff2",
        ".ttf",
        ".eot",
        ".pyc",
        ".class",
        ".o",
        ".obj",
    }
)

DEFAULT_KNOWLEDGE_SUFFIXES: frozenset[str] = STRUCTURED_SUFFIXES | TEXT_SUFFIXES | IMAGE_SUFFIXES


class ExtractError(Exception):
    """单文件抽取失败（可跳过继续扫目录）。"""


def supported_suffixes() -> frozenset[str]:
    return DEFAULT_KNOWLEDGE_SUFFIXES


def _read_text_file(path: Path, encoding: str = "utf-8") -> str:
    raw = path.read_bytes()
    encodings = [encoding, "utf-8-sig", "utf-8", "gb18030", "gbk", "latin-1"]
    seen: set[str] = set()
    for enc in encodings:
        if enc in seen:
            continue
        seen.add(enc)
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ExtractError(f"无法解码文本: {path}")


def _extract_plain(path: Path, encoding: str = "utf-8") -> str:
    return _read_text_file(path, encoding=encoding).strip()


def _extract_html(path: Path, encoding: str = "utf-8") -> str:
    text = _read_text_file(path, encoding=encoding)
    text = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", text)
    text = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def _rows_to_markdown(rows: list[list[str]], *, title: str = "") -> str:
    """将二维表转为 Markdown 表格（利于检索）；无表头时用 Col1..N。"""
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    norm = [list(r) + [""] * (width - len(r)) for r in rows]
    header = norm[0]
    if all(h.strip() for h in header):
        body = norm[1:]
        heads = header
    else:
        heads = [f"列{i}" for i in range(1, width + 1)]
        body = norm

    def esc(cell: str) -> str:
        return cell.replace("|", "\\|").replace("\n", " ").strip()

    lines: list[str] = []
    if title:
        lines.append(f"## {title}")
    lines.append("| " + " | ".join(esc(h) or " " for h in heads) + " |")
    lines.append("| " + " | ".join("---" for _ in heads) + " |")
    for row in body:
        lines.append("| " + " | ".join(esc(c) or " " for c in row) + " |")
    return "\n".join(lines)


def _extract_csv(path: Path, encoding: str = "utf-8", *, delimiter: str = ",") -> str:
    from app.config import settings

    text = _read_text_file(path, encoding=encoding)
    reader = csv.reader(StringIO(text), delimiter=delimiter)
    rows: list[list[str]] = []
    max_rows = max(1, settings.knowledge_table_max_rows)
    for i, row in enumerate(reader):
        if i >= max_rows:
            rows.append([f"…（已截断，仅保留前 {max_rows} 行）"])
            break
        cells = [c.strip() for c in row]
        if any(cells):
            rows.append(cells)
    return _rows_to_markdown(rows, title=path.name).strip()


def _extract_docx(path: Path, encoding: str = "utf-8") -> str:
    del encoding
    try:
        from docx import Document
    except ImportError as exc:
        raise ExtractError("缺少依赖 python-docx，请 uv sync") from exc

    doc = Document(str(path))
    parts: list[str] = []
    for para in doc.paragraphs:
        t = (para.text or "").strip()
        if t:
            parts.append(t)
    for ti, table in enumerate(doc.tables, start=1):
        rows: list[list[str]] = []
        for row in table.rows:
            cells = [((c.text or "").strip()) for c in row.cells]
            rows.append(cells)
        md = _rows_to_markdown(rows, title=f"Word表格{ti}")
        if md:
            parts.append(md)
    return "\n\n".join(parts).strip()


def _extract_pptx(path: Path, encoding: str = "utf-8") -> str:
    del encoding
    try:
        from pptx import Presentation
        from pptx.enum.shapes import MSO_SHAPE_TYPE
    except ImportError as exc:
        raise ExtractError("缺少依赖 python-pptx，请 uv sync") from exc

    prs = Presentation(str(path))
    parts: list[str] = []
    for i, slide in enumerate(prs.slides, start=1):
        slide_bits: list[str] = []
        for shape in slide.shapes:
            # BaseShape 无 text/table 静态属性；运行时按类型探测
            text_val = getattr(shape, "text", None)
            if isinstance(text_val, str):
                t = text_val.strip()
                if t:
                    slide_bits.append(t)
            # 幻灯片内嵌表格
            if shape.shape_type == MSO_SHAPE_TYPE.TABLE:
                table = getattr(shape, "table", None)
                if table is None:
                    continue
                rows: list[list[str]] = []
                for row in table.rows:
                    rows.append([(cell.text or "").strip() for cell in row.cells])
                md = _rows_to_markdown(rows, title=f"幻灯片{i}表格")
                if md:
                    slide_bits.append(md)
        if slide_bits:
            parts.append(f"[幻灯片 {i}]\n" + "\n".join(slide_bits))
    return "\n\n".join(parts).strip()


def _extract_pdf(path: Path, encoding: str = "utf-8") -> str:
    del encoding
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ExtractError("缺少依赖 pypdf，请 uv sync") from exc

    reader = PdfReader(str(path))
    parts: list[str] = []
    for i, page in enumerate(reader.pages, start=1):
        try:
            t = (page.extract_text() or "").strip()
        except Exception as exc:  # noqa: BLE001
            logger.warning("PDF 第 %s 页抽取失败 %s: %s", i, path, exc)
            continue
        if t:
            parts.append(f"[第 {i} 页]\n{t}")
    return "\n\n".join(parts).strip()


def _extract_xlsx(path: Path, encoding: str = "utf-8") -> str:
    del encoding
    from app.config import settings

    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise ExtractError("缺少依赖 openpyxl，请 uv sync") from exc

    max_rows = max(1, settings.knowledge_table_max_rows)
    wb = load_workbook(str(path), read_only=True, data_only=True)
    parts: list[str] = []
    for sheet in wb.worksheets:
        rows: list[list[str]] = []
        for i, row in enumerate(sheet.iter_rows(values_only=True)):
            if i >= max_rows:
                rows.append([f"…（已截断，仅保留前 {max_rows} 行）"])
                break
            cells = ["" if c is None else str(c).strip() for c in row]
            if any(cells):
                # 去掉尾部空列
                while cells and not cells[-1]:
                    cells.pop()
                rows.append(cells)
        md = _rows_to_markdown(rows, title=f"工作表 {sheet.title}")
        if md:
            parts.append(md)
    wb.close()
    return "\n\n".join(parts).strip()


def _extract_xls(path: Path, encoding: str = "utf-8") -> str:
    """旧版 Excel .xls（需 xlrd）。"""
    del encoding
    from app.config import settings

    try:
        import xlrd
    except ImportError as exc:
        raise ExtractError("缺少依赖 xlrd，无法解析 .xls；请 uv add xlrd 或另存为 .xlsx") from exc

    max_rows = max(1, settings.knowledge_table_max_rows)
    book = xlrd.open_workbook(str(path))
    parts: list[str] = []
    for sheet in book.sheets():
        rows: list[list[str]] = []
        limit = min(sheet.nrows, max_rows)
        for r in range(limit):
            cells = [str(sheet.cell_value(r, c)).strip() for c in range(sheet.ncols)]
            if any(cells):
                rows.append(cells)
        if sheet.nrows > max_rows:
            rows.append([f"…（已截断，仅保留前 {max_rows} 行）"])
        md = _rows_to_markdown(rows, title=f"工作表 {sheet.name}")
        if md:
            parts.append(md)
    return "\n\n".join(parts).strip()


def _extract_image(path: Path, encoding: str = "utf-8") -> str:
    del encoding
    from app.infrastructure.vector.vision import VisionExtractError, extract_image_text

    try:
        return extract_image_text(path)
    except VisionExtractError as exc:
        raise ExtractError(str(exc)) from exc


_EXTRACTORS: dict[str, Callable[[Path, str], str]] = {
    ".docx": _extract_docx,
    ".pptx": _extract_pptx,
    ".pdf": _extract_pdf,
    ".xlsx": _extract_xlsx,
    ".xls": _extract_xls,
    ".html": _extract_html,
    ".htm": _extract_html,
    ".csv": _extract_csv,
    ".tsv": lambda p, e: _extract_csv(p, e, delimiter="\t"),
    **{suf: _extract_image for suf in IMAGE_SUFFIXES},
}


def extract_text(path: Path | str, *, encoding: str = "utf-8") -> str:
    """
    从文件抽取纯文本（含表格 Markdown、图片 VL 结果）。
    """
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    suffix = file_path.suffix.lower()
    if suffix in UNSUPPORTED_BINARY_SUFFIXES:
        raise ExtractError(
            f"不支持的格式 {suffix}（{file_path.name}）。"
            f"请将 .doc/.ppt 另存为 .docx/.pptx；音视频需 ASR（未在知识库启用）。"
        )

    extractor = _EXTRACTORS.get(suffix)
    if extractor is not None:
        text = extractor(file_path, encoding)
    else:
        text = _extract_plain(file_path, encoding=encoding)

    if not (text or "").strip():
        raise ExtractError(f"抽取结果为空: {file_path}")
    return text.strip()
