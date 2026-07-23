"""根据时间间隔和长度规则，将长歌词切成更适合跟拍的短句。"""

from __future__ import annotations

import re
from typing import Sequence


def split_lyrics_by_rhythm(
    lyrics: Sequence[tuple[float, float, str]],
    *,
    max_chars: int = 28,
    min_gap: float = 2.0,
) -> list[tuple[float, float, str]]:
    """按节奏和长度切分歌词。"""
    if not lyrics:
        return []

    result: list[tuple[float, float, str]] = []
    for start, end, text in lyrics:
        text = text.strip()
        if not text:
            continue

        if len(text) <= max_chars or end - start < min_gap:
            result.append((start, end, text))
            continue

        if len(text) < max_chars + 8:
            result.append((start, end, text))
            continue

        pieces = _split_text(text, max_chars=max_chars)
        if len(pieces) == 1:
            result.append((start, end, text))
            continue

        duration = max(end - start, 0.1)
        step = duration / len(pieces)
        for idx, piece in enumerate(pieces):
            piece_start = start + idx * step
            piece_end = start + (idx + 1) * step
            result.append((piece_start, piece_end, piece))

    return result


def _split_text(text: str, *, max_chars: int) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) <= max_chars:
        return [cleaned]

    parts = re.split(r"([，。！？；：,])", cleaned)
    candidates: list[str] = []
    current = ""
    for part in parts:
        if not part:
            continue
        if len(current) + len(part) <= max_chars:
            current += part
        else:
            if current:
                candidates.append(current.strip())
            current = part
    if current:
        candidates.append(current.strip())

    if len(candidates) <= 1:
        words = re.split(r"([，。！？；：,\s])", cleaned)
        current = ""
        candidates = []
        for word in words:
            if not word:
                continue
            if len(current) + len(word) <= max_chars:
                current += word
            else:
                if current:
                    candidates.append(current.strip())
                current = word
        if current:
            candidates.append(current.strip())

    return [c for c in candidates if c]
