"""为歌词生成提供联网搜索与官方歌词文本提取。"""

from __future__ import annotations

import os
import re
from typing import Any, Sequence

import urllib.parse

import requests


DEFAULT_SEARCH_ENGINE = os.getenv("WEB_SEARCH_ENGINE", "https://cn.bing.com/search?q=")
DEFAULT_TIMEOUT = int(os.getenv("WEB_SEARCH_TIMEOUT", "10"))


def extract_lyrics_lines_from_html(html: str) -> list[str]:
    """从网页 HTML 中提取歌词行。"""
    if not html:
        return []

    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.I | re.S)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", "\n", text)
    text = html_unescape(text)
    lines = []
    for raw in text.splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        if not line:
            continue
        if len(line) < 2:
            continue
        if line.startswith("http"):
            continue
        if line.lower() in {"lyrics", "lyric", "song", "verse", "chorus", "bridge"}:
            continue
        if any(token in line.lower() for token in ["copyright", "all rights reserved", "lyrics"]):
            continue
        lines.append(line)

    return lines[:40]


def html_unescape(text: str) -> str:
    import html
    return html.unescape(text)


def _extract_lyric_candidates(text: str) -> list[dict[str, Any]]:
    """从网页内容中提取可能的歌词线索。"""
    candidates: list[dict[str, Any]] = []
    for chunk in re.split(r"\n{2,}", text):
        chunk = re.sub(r"<[^>]+>", " ", chunk)
        chunk = re.sub(r"\s+", " ", chunk).strip()
        if not chunk:
            continue
        if len(chunk) < 8:
            continue
        if any(k in chunk.lower() for k in ["lyrics", "lyric", "song", "chorus", "verse"]):
            candidates.append({"title": chunk[:80], "snippet": chunk[:240]})
    return candidates[:6]


def search_web(query: str, *, timeout: int | None = None) -> list[dict[str, Any]]:
    """执行一个简单的网页搜索，返回标题/摘要/链接列表。"""
    if not query:
        return []

    endpoint = os.getenv("WEB_SEARCH_ENDPOINT", DEFAULT_SEARCH_ENGINE)
    url = f"{endpoint}{urllib.parse.quote(query)}"
    response = requests.get(url, timeout=timeout or DEFAULT_TIMEOUT)
    response.raise_for_status()

    text = response.text
    if not text:
        return []

    results: list[dict[str, Any]] = []

    for match in re.finditer(r'<a[^>]+href=["\']([^"\']+)[^>]*>(.*?)</a>', text, flags=re.I | re.S):
        href = match.group(1).strip()
        anchor = re.sub(r'<[^>]+>', ' ', match.group(2))
        anchor = re.sub(r'\s+', ' ', anchor).strip()
        if not href or not anchor:
            continue
        if href.startswith("http"):
            results.append({"title": anchor[:120], "url": href, "snippet": anchor[:240]})
            break

    if not results:
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("http://") or line.startswith("https://"):
                results.append({"title": "搜索结果", "url": line, "snippet": line})
                break

    if not results:
        results = _extract_lyric_candidates(text)

    return results[:5]


def fetch_official_lyrics(query: str, *, timeout: int | None = None) -> list[str]:
    """优先搜索并抓取可能的官方歌词文本。"""
    results = search_web(query, timeout=timeout)
    if not results:
        return []

    lines: list[str] = []
    seen: set[str] = set()
    for item in results:
        url = str(item.get("url", "")).strip()
        if not url or url in seen:
            continue
        seen.add(url)
        try:
            response = requests.get(url, timeout=timeout or DEFAULT_TIMEOUT)
            response.raise_for_status()
            extracted = extract_lyrics_lines_from_html(response.text)
            if extracted:
                lines.extend(extracted)
        except Exception:
            continue
        if lines:
            break

    return lines[:40]
