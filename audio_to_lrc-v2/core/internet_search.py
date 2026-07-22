"""联网搜索：歌词、专辑、封面、歌曲名、歌手名：支持 lrclib、网易云、QQ音乐、酷狗"""

import re
import requests
from typing import Optional
from difflib import SequenceMatcher

import syncedlyrics


# 标题/歌手匹配的最低相似度阈值
_MIN_TITLE_SIMILARITY = 0.5
_MIN_ARTIST_SIMILARITY = 0.4

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


# ── 主搜索入口 ──────────────────────────────────────────────────────────────


def search_lyrics(
    title: str,
    artist: str = "",
    providers: list[str] | None = None,
) -> Optional[tuple[str, str, dict]]:
    """
    从多个平台搜索同步歌词（带时间戳的 LRC 格式）及歌曲信息。

    返回: (lrc_text, provider_name, song_info) 或 None
    song_info: {"album": str, "cover_url": str}（可能为空值）
    """
    if not title:
        return None

    all_providers = ["QQMusic", "Kugou", "NetEase", "lrclib"]
    if providers is None:
        providers = all_providers
    else:
        providers = [p for p in providers if p in all_providers]

    # 第一轮：优先查找同步歌词
    for provider in providers:
        try:
            result = _search_provider_full(provider, title, artist, synced_only=True)
            if result:
                lrc_text, song_info = result
                if lrc_text and _has_timestamps(lrc_text):
                    return lrc_text, provider, song_info
        except Exception:
            continue

    # 第二轮：放宽限制，接受任何带时间戳的结果
    for provider in providers:
        try:
            result = _search_provider_full(provider, title, artist, synced_only=False)
            if result:
                lrc_text, song_info = result
                if lrc_text and _has_timestamps(lrc_text):
                    return lrc_text, provider, song_info
        except Exception:
            continue

    return None


def search_song_info(
    title: str,
    artist: str = "",
    providers: list[str] | None = None,
) -> Optional[dict]:
    """
    仅搜索歌曲名称、歌手以及专辑信息和封面 URL（不需要歌词）。

    返回: {"album": str, "cover_url": str, "matched_title": str, "matched_artist": str} 或 None
    """
    if not title:
        return None

    all_providers = ["QQMusic", "Kugou", "NetEase"]
    if providers is None:
        providers = all_providers
    else:
        providers = [p for p in providers if p in all_providers]

    for provider in providers:
        try:
            info = _search_song_info_provider(provider, title, artist)
            if info and (info.get("album") or info.get("cover_url")
                         or info.get("matched_title") or info.get("matched_artist")):
                return info
        except Exception:
            continue

    return None


# ── 各平台分发 ──────────────────────────────────────────────────────────────


def _search_provider_full(
    provider: str, title: str, artist: str, synced_only: bool
) -> Optional[tuple[str, dict]]:
    """搜索歌词 + 歌曲信息，返回 (lrc_text, song_info) 或 None"""
    search_term = f"{artist} {title}".strip() if artist else title

    if provider in ("lrclib", "NetEase"):
        lrc = syncedlyrics.search(
            search_term, synced_only=synced_only, providers=[provider]
        )
        if lrc:
            # lrclib/NetEase 不提供封面，但可以尝试独立搜索歌曲信息
            info = _search_song_info_provider(provider, title, artist) or {}
            return lrc, info
        return None

    elif provider == "QQMusic":
        return _search_qq_music(title, artist)
    elif provider == "Kugou":
        return _search_kugou(title, artist)
    return None


def _search_song_info_provider(
    provider: str, title: str, artist: str
) -> Optional[dict]:
    """从指定平台搜索歌曲专辑/封面信息"""
    if provider == "QQMusic":
        return _qq_music_info(title, artist)
    elif provider == "Kugou":
        return _kugou_info(title, artist)
    elif provider == "NetEase":
        return _netease_info(title, artist)
    return None


# ── QQ 音乐 ─────────────────────────────────────────────────────────────────


def _search_qq_music(title: str, artist: str) -> Optional[tuple[str, dict]]:
    """从 QQ 音乐搜索歌词 + 专辑/封面"""
    try:
        url = (
            "https://c.y.qq.com/soso/fcgi-bin/client_search_cp"
            f"?w={requests.utils.quote(title + ' ' + artist)}"
            "&format=json&n=5"
        )
        headers = {"Referer": "https://y.qq.com", "User-Agent": _UA}
        resp = requests.get(url, headers=headers, timeout=8)
        songs = resp.json().get("data", {}).get("song", {}).get("list", [])

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
            lyric = lrc_resp.json().get("lyric", "")

            # 提取专辑/封面/歌曲名/歌手名
            album_name = song.get("albumname", "")
            album_mid = song.get("albummid", "")
            cover_url = ""
            if album_mid:
                cover_url = (
                    f"https://y.qq.com/music/photo_new/T002R300x300M000{album_mid}.jpg"
                )

            song_info = {
                "album": album_name,
                "cover_url": cover_url,
                "matched_title": song_name,
                "matched_artist": singers,
            }

            if lyric and _has_timestamps(lyric):
                return lyric, song_info
            return None

    except Exception:
        pass
    return None


def _qq_music_info(title: str, artist: str) -> Optional[dict]:
    """仅从 QQ 音乐获取专辑/封面信息"""
    try:
        url = (
            "https://c.y.qq.com/soso/fcgi-bin/client_search_cp"
            f"?w={requests.utils.quote(title + ' ' + artist)}"
            "&format=json&n=3"
        )
        headers = {"Referer": "https://y.qq.com", "User-Agent": _UA}
        resp = requests.get(url, headers=headers, timeout=8)
        songs = resp.json().get("data", {}).get("song", {}).get("list", [])

        for song in songs:
            song_name = song.get("songname", "")
            singers = " ".join(s.get("name", "") for s in song.get("singer", []))
            if not _is_match(title, song_name, artist, singers):
                continue
            album_name = song.get("albumname", "")
            album_mid = song.get("albummid", "")
            cover_url = ""
            if album_mid:
                cover_url = (
                    f"https://y.qq.com/music/photo_new/T002R300x300M000{album_mid}.jpg"
                )
            return {
                "album": album_name,
                "cover_url": cover_url,
                "matched_title": song_name,
                "matched_artist": singers,
            }
    except Exception:
        pass
    return None


# ── 酷狗音乐 ────────────────────────────────────────────────────────────────


def _search_kugou(title: str, artist: str) -> Optional[tuple[str, dict]]:
    """从酷狗音乐搜索歌词 + 专辑/封面"""
    try:
        search_kw = f"{artist} {title}".strip()
        url = (
            "https://songsearch.kugou.com/song_search_v2"
            f"?keyword={requests.utils.quote(search_kw)}&page_size=5"
        )
        resp = requests.get(url, headers={"User-Agent": _UA}, timeout=8)
        songs = resp.json().get("data", {}).get("lists", [])

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
            content_resp = requests.get(content_url, headers={"User-Agent": _UA}, timeout=8)
            content_data = content_resp.json()
            import base64
            content_b64 = content_data.get("content", "")
            lyric = ""
            if content_b64:
                lyric = base64.b64decode(content_b64).decode("utf-8", errors="ignore")

            # 提取专辑/封面/歌曲名/歌手名
            album_name = song.get("AlbumName", "")
            album_id = song.get("AlbumID", "")
            cover_url = ""
            if album_id:
                cover_url = (
                    f"https://imge.kugou.com/stdmusic/150/{album_id}.jpg"
                )

            song_info = {
                "album": album_name,
                "cover_url": cover_url,
                "matched_title": song_name,
                "matched_artist": singer,
            }

            if lyric and _has_timestamps(lyric):
                return lyric, song_info
            return None

    except Exception:
        pass
    return None


def _kugou_info(title: str, artist: str) -> Optional[dict]:
    """仅从酷狗获取专辑/封面信息"""
    try:
        search_kw = f"{artist} {title}".strip()
        url = (
            "https://songsearch.kugou.com/song_search_v2"
            f"?keyword={requests.utils.quote(search_kw)}&page_size=3"
        )
        resp = requests.get(url, headers={"User-Agent": _UA}, timeout=8)
        songs = resp.json().get("data", {}).get("lists", [])
        for song in songs:
            song_name = song.get("SongName", "").replace("<em>", "").replace("</em>", "")
            singer = song.get("SingerName", "").replace("<em>", "").replace("</em>", "")
            if not _is_match(title, song_name, artist, singer):
                continue
            album_name = song.get("AlbumName", "")
            album_id = song.get("AlbumID", "")
            cover_url = ""
            if album_id:
                cover_url = f"https://imge.kugou.com/stdmusic/150/{album_id}.jpg"
            return {
                "album": album_name,
                "cover_url": cover_url,
                "matched_title": song_name,
                "matched_artist": singer,
            }
    except Exception:
        pass
    return None


# ── 网易云音乐 ──────────────────────────────────────────────────────────────


def _netease_info(title: str, artist: str) -> Optional[dict]:
    """从网易云获取专辑/封面信息"""
    try:
        search_kw = f"{artist} {title}".strip()
        url = (
            "https://music.163.com/api/search/get/web"
            f"?s={requests.utils.quote(search_kw)}&type=1&limit=5"
        )
        headers = {"Referer": "https://music.163.com", "User-Agent": _UA}
        resp = requests.post(url, headers=headers, timeout=8)
        songs = resp.json().get("result", {}).get("songs", [])
        for song in songs:
            song_name = song.get("name", "")
            singers = " ".join(s.get("name", "") for s in song.get("artists", []))
            if not _is_match(title, song_name, artist, singers):
                continue
            album = song.get("album", {})
            album_name = album.get("name", "")
            cover_url = album.get("picUrl", "")
            return {
                "album": album_name,
                "cover_url": cover_url,
                "matched_title": song_name,
                "matched_artist": singers,
            }
    except Exception:
        pass
    return None


# ── 工具函数 ────────────────────────────────────────────────────────────────


def _has_timestamps(lrc_text: str) -> bool:
    """检查歌词是否包含 LRC 时间戳格式 [mm:ss.xx]"""
    pattern = re.compile(r"\[\d{1,3}:\d{2}(?:\.\d{1,3})?\]")
    return bool(pattern.search(lrc_text))


def _normalize(text: str) -> str:
    """标准化文本：去除括号、特殊符号、多余空格，统一小写"""
    text = text.lower().strip()
    text = re.sub(r"[\(（\[【].*?[\)）\]】]", "", text)
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
    """校验搜索结果的歌曲是否与目标匹配"""
    title_sim = _similarity(_normalize(expected_title), _normalize(actual_title))
    if title_sim < _MIN_TITLE_SIMILARITY:
        return False
    if expected_artist and actual_artist:
        artist_sim = _similarity(
            _normalize(expected_artist), _normalize(actual_artist)
        )
        if artist_sim < _MIN_ARTIST_SIMILARITY:
            return False
    return True
