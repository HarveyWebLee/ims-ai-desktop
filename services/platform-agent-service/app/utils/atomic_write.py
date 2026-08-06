"""跨平台原子写文件（Windows 对已占用目标的 os.replace 常抛 WinError 5/32）。"""

from __future__ import annotations

import logging
import os
import time
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

# Windows：5=拒绝访问，32=正被另一进程使用
_RETRYABLE_WINERRORS = frozenset({5, 32})


def _is_retryable_replace_error(exc: OSError) -> bool:
    winerror = getattr(exc, "winerror", None)
    if winerror in _RETRYABLE_WINERRORS:
        return True
    return isinstance(exc, PermissionError)


def _atomic_replace(tmp: Path, path: Path, *, retries: int, base_delay_s: float) -> None:
    last_err: OSError | None = None
    for attempt in range(max(1, retries)):
        try:
            os.replace(tmp, path)
            return
        except OSError as exc:
            if not _is_retryable_replace_error(exc):
                raise
            last_err = exc
            time.sleep(base_delay_s * (attempt + 1))
    raise OSError(f"原子替换失败 path={path}: {last_err}") from last_err


def atomic_write_text(
    path: Path,
    text: str,
    *,
    encoding: str = "utf-8",
    retries: int = 8,
    base_delay_s: float = 0.05,
) -> None:
    """先写唯一临时文件再 replace；失败时短退避重试，仍失败则直写目标。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        tmp.write_text(text, encoding=encoding)
        try:
            _atomic_replace(tmp, path, retries=retries, base_delay_s=base_delay_s)
            return
        except OSError as exc:
            logger.warning("原子替换失败，回退直写 path=%s err=%s", path, exc)
            path.write_text(text, encoding=encoding)
    finally:
        if tmp.is_file():
            try:
                tmp.unlink()
            except OSError:
                pass


def atomic_write_bytes(
    path: Path,
    data: bytes,
    *,
    retries: int = 8,
    base_delay_s: float = 0.05,
) -> None:
    """二进制版原子写，语义同 atomic_write_text。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        tmp.write_bytes(data)
        try:
            _atomic_replace(tmp, path, retries=retries, base_delay_s=base_delay_s)
            return
        except OSError as exc:
            logger.warning("原子替换失败，回退直写 path=%s err=%s", path, exc)
            path.write_bytes(data)
    finally:
        if tmp.is_file():
            try:
                tmp.unlink()
            except OSError:
                pass
