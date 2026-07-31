"""
纯文本切块：按字符窗口切分，带重叠，避免引入额外分词依赖。
"""

from __future__ import annotations


def chunk_text(
    text: str,
    *,
    chunk_size: int = 800,
    chunk_overlap: int = 120,
) -> list[str]:
    """
    将长文本切成带重叠的片段。

    - 优先在换行处断开，减少半句截断
    - ``chunk_overlap`` 须小于 ``chunk_size``
    """
    normalized = text.replace("\r\n", "\n").strip()
    if not normalized:
        return []
    if chunk_size <= 0:
        raise ValueError("chunk_size 必须为正整数")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap 须满足 0 <= overlap < chunk_size")

    if len(normalized) <= chunk_size:
        return [normalized]

    chunks: list[str] = []
    start = 0
    length = len(normalized)
    while start < length:
        end = min(start + chunk_size, length)
        if end < length:
            # 向后找换行，避免硬切到行中部（最多回退 overlap 范围）
            window = normalized[start:end]
            nl = window.rfind("\n")
            if nl > chunk_size // 4:
                end = start + nl + 1
        piece = normalized[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= length:
            break
        start = max(0, end - chunk_overlap)
    return chunks
