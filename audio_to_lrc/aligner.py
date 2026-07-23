"""将官方歌词文本与 Whisper 识别时间片段对齐。"""

from __future__ import annotations

import difflib
import re
from typing import Sequence


def _normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def align_lyrics_to_audio(recognized_segments: Sequence[tuple[float, float, str]],
                          official_lines: Sequence[str]) -> list[tuple[float, float, str]]:
    """把官方歌词行按顺序映射到 Whisper 的识别片段。"""
    if not recognized_segments:
        return []

    cleaned_official = [line.strip() for line in official_lines if str(line).strip()]
    if not cleaned_official:
        return []

    aligned: list[tuple[float, float, str]] = []
    segment_index = 0

    for line in cleaned_official:
        if segment_index >= len(recognized_segments):
            break

        start, end, _ = recognized_segments[segment_index]
        normalized_line = _normalize_text(line)
        candidate = recognized_segments[segment_index][2]
        candidate_norm = _normalize_text(candidate)

        if normalized_line and candidate_norm:
            ratio = difflib.SequenceMatcher(None, normalized_line, candidate_norm).ratio()
            if ratio < 0.35 and len(normalized_line.split()) >= 2:
                for idx in range(segment_index + 1, min(len(recognized_segments), segment_index + 3)):
                    other_start, other_end, other_text = recognized_segments[idx]
                    other_norm = _normalize_text(other_text)
                    if not other_norm:
                        continue
                    other_ratio = difflib.SequenceMatcher(None, normalized_line, other_norm).ratio()
                    if other_ratio > ratio:
                        segment_index = idx
                        start, end, candidate = other_start, other_end, other_text
                        candidate_norm = other_norm
                        ratio = other_ratio
                        break

        aligned.append((start, end, line))
        segment_index += 1

    if not aligned:
        return []

    return aligned
