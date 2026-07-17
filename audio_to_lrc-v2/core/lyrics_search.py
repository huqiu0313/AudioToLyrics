"""联网歌词搜索：支持 lrclib、网易云音乐、QQ音乐、酷狗音乐"""

import re
import requests
from typing import Optional
from difflib import SequenceMatcher

import syncedlyrics


# 标题/歌手匹配的最低相似度阈值
_MIN_TITLE_SIMILARITY = 0.5
_MIN_ARTIST_SIMILARITY = 0.4


# ── 主搜索入口 ──────────────────────────────────────────────────────────────


def search_lyrics(
    title: str,
    artist: str = "",
    providers: list[str] | None = None,
) -> Optional[tuple[str, str]]:
    """
    从多个平台搜索同步歌词（带时间戳的 LRC 格式）。

    按优先级依次查询各平台，找到第一个带同步歌词的结果立即返回。
    全部未找到则返回 None。

    返回: (lrc_text, provider_name) 或 None
    """
    if not title:
        return None

    all_providers = ["QQMusic", "Kugou", "lrclib", "NetEase"]
    if providers is None:
        providers = all_providers
    else:
        providers = [p for p in providers if p in all_providers]

    # 第一轮：优先查找同步歌词
    for provider in providers:
        try:
            lrc_text = _search_provider(provider, title, artist, synced_only=True)
            if lrc_text and _has_timestamps(lrc_text):
                return lrc_text, provider
        except Exception:
            continue

    # 第二轮：放宽限制，接受任何带时间戳的结果
    for provider in providers:
        try:
            lrc_text = _search_provider(provider, title, artist, synced_only=False)
            if lrc_text and _has_timestamps(lrc_text):
                return lrc_text, provider
        except Exception:
            continue

    return None


# ── 各平台分发 ──────────────────────────────────────────────────────────────


def _search_provider(
    provider: str, title: str, artist: str, synced_only: bool
) -> Optional[str]:
    """根据平台名称调用对应的搜索实现"""
    search_term = f"{artist} {title}".strip() if artist else title

    if provider in ("lrclib", "NetEase"):
        return syncedlyrics.search(
            search_term, synced_only=synced_only, providers=[provider]
        )
    elif provider == "QQMusic":
        return _search_qq_music(title, artist)
    elif provider == "Kugou":
        return _search_kugou(title, artist)
    return None


# ── QQ 音乐歌词搜索 ────────────────────────────────────────────────────────


def _search_qq_music(title: str, artist: str) -> Optional[str]:
    """从 QQ 音乐搜索 LRC 歌词"""
    try:
        # 搜索歌曲
        url = (
            "https://c.y.qq.com/soso/fcgi-bin/client_search_cp"
            f"?w={requests.utils.quote(title + ' ' + artist)}"
            "&format=json&n=5"
        )
        headers = {"Referer": "https://y.qq.com", "User-Agent": _UA}
        resp = requests.get(url, headers=headers, timeout=8)
        data = resp.json()
        songs = data.get("data", {}).get("song", {}).get("list", [])
        if not songs:
            return None

        # 遍历结果，找到标题匹配的曲目
        for song in songs:
            song_name = song.get("songname", "")
            singers = " ".join(s.get("name", "") for s in song.get("singer", []))
            if not _is_match(title, song_name, artist, singers):
                continue
            song_mid = song.get("songmid", "")
            if not song_mid:
                continue
            # 获取歌词
            lrc_url = (
                "https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg"
                f"?songmid={song_mid}&format=json&nobase64=1"
            )
            lrc_resp = requests.get(lrc_url, headers=headers, timeout=8)
            lrc_data = lrc_resp.json()
            lyric = lrc_data.get("lyric", "")
            if lyric and _has_timestamps(lyric):
                return lyric
    except Exception:
        pass
    return None


# ── 酷狗音乐歌词搜索 ──────────────────────────────────────────────────────


def _search_kugou(title: str, artist: str) -> Optional[str]:
    """从酷狗音乐搜索 LRC 歌词"""
    try:
        search_kw = f"{artist} {title}".strip()
        url = (
            "https://songsearch.kugou.com/song_search_v2"
            f"?keyword={requests.utils.quote(search_kw)}&page_size=5"
        )
        resp = requests.get(url, headers={"User-Agent": _UA}, timeout=8)
        data = resp.json()
        songs = data.get("data", {}).get("lists", [])
        if not songs:
            return None

        # 遍历结果，找到标题匹配的曲目
        for song in songs:
            song_name = song.get("SongName", "").replace("<em>", "").replace("</em>", "")
            singer = song.get("SingerName", "").replace("<em>", "").replace("</em>", "")
            if not _is_match(title, song_name, artist, singer):
                continue
            song_hash = song.get("FileHash", "")
            if not song_hash:
                continue
            # 获取歌词
            lrc_url = (
                f"https://krcs.kugou.com/search"
                f"?ver=1&man=yes&client=mobi&hash={song_hash}"
            )
            lrc_resp = requests.get(lrc_url, headers={"User-Agent": _UA}, timeout=8)
            lrc_data = lrc_resp.json()

            lyric_id = lrc_data.get("candidates", [{}])[0].get("id", "")
            lyric_key = lrc_data.get("candidates", [{}])[0].get("accesskey", "")
            if not lyric_id or not lyric_key:
                continue

            content_url = (
                f"https://krcs.kugou.com/download"
                f"?ver=1&client=mobi&id={lyric_id}&accesskey={lyric_key}"
            )
            content_resp = requests.get(
                content_url, headers={"User-Agent": _UA}, timeout=8
            )
            content_data = content_resp.json()
            import base64
            content_b64 = content_data.get("content", "")
            if content_b64:
                lyric = base64.b64decode(content_b64).decode("utf-8", errors="ignore")
                if lyric and _has_timestamps(lyric):
                    return lyric
    except Exception:
        pass
    return None


# ── 工具函数 ────────────────────────────────────────────────────────────────

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _has_timestamps(lrc_text: str) -> bool:
    """检查歌词是否包含 LRC 时间戳格式 [mm:ss.xx]"""
    pattern = re.compile(r"\[\d{1,3}:\d{2}(?:\.\d{1,3})?\]")
    return bool(pattern.search(lrc_text))


def _normalize(text: str) -> str:
    """标准化文本：去除括号、特殊符号、多余空格，统一小写"""
    text = text.lower().strip()
    # 去除常见后缀如 (Live)、(Remix)、【】、（）等
    text = re.sub(r"[\(（\[【].*?[\)）\]】]", "", text)
    # 去除特殊符号
    text = re.sub(r"[^\w\u4e00-\u9fff\s]", "", text)
    return text.strip()


def _similarity(a: str, b: str) -> float:
    """计算两个字符串的相似度（0~1）"""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _is_match(
    expected_title: str, actual_title: str,
    expected_artist: str = "", actual_artist: str = "",
) -> bool:
    """
    校验搜索结果的歌曲是否与目标歌曲匹配。
    标题必须相似，歌手（如有）也必须相似。
    """
    norm_expected = _normalize(expected_title)
    norm_actual = _normalize(actual_title)

    title_sim = _similarity(norm_expected, norm_actual)
    if title_sim < _MIN_TITLE_SIMILARITY:
        return False

    # 如果提供了歌手信息，也校验歌手
    if expected_artist and actual_artist:
        artist_sim = _similarity(
            _normalize(expected_artist), _normalize(actual_artist)
        )
        if artist_sim < _MIN_ARTIST_SIMILARITY:
            return False

    return True
