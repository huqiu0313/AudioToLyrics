"""联网搜索：歌词、专辑、封面、歌曲名、歌手名（QQ音乐/酷狗/网易云/lrclib）

架构：各平台实现 LyricsProvider 接口并注册到 _PROVIDERS，
搜索入口按 config.LYRICS_PROVIDERS 优先级顺序分发。
"""

import base64
import re
import requests
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from typing import Optional

import syncedlyrics

from config import (
    COVER_DOWNLOAD_TIMEOUT,
    COVER_MIN_BYTES,
    HTTP_TIMEOUT,
    LYRICS_PROVIDERS,
)
from utils.logging_setup import get_logger

logger = get_logger(__name__)

# 标题/歌手匹配的最低相似度阈值
_MIN_TITLE_SIMILARITY = 0.5
_MIN_ARTIST_SIMILARITY = 0.4

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# 封面下载防盗链 Referer（按 URL 中包含的域名匹配）
_COVER_REFERERS = {
    "qq.com": "https://y.qq.com",
    "kugou.com": "https://www.kugou.com",
    "163.com": "https://music.163.com",
}


@dataclass
class SongInfo:
    """搜索匹配到的歌曲信息（空字符串表示未获取到）"""

    album: str = ""
    cover_url: str = ""
    matched_title: str = ""
    matched_artist: str = ""

    def is_empty(self) -> bool:
        return not any(
            (self.album, self.cover_url, self.matched_title, self.matched_artist)
        )


# ── 主搜索入口 ──────────────────────────────────────────────────────────────


def search_lyrics(
    title: str,
    artist: str = "",
    providers: list[str] | tuple[str, ...] | None = None,
) -> Optional[tuple[str, str, dict]]:
    """
    从多个平台搜索同步歌词（带时间戳的 LRC 格式）及歌曲信息。

    返回: (lrc_text, provider_name, song_info) 或 None
    song_info: {"album": str, "cover_url": str, ...}（值可能为空字符串）
    """
    if not title:
        return None

    resolved = _resolve_providers(providers, for_info=False)

    # 第一轮：优先查找同步歌词；第二轮：放宽限制接受任何结果
    for synced_only in (True, False):
        for provider in resolved:
            try:
                result = provider.search_lyrics(title, artist, synced_only)
            except Exception as e:
                # 单平台失败是常态（网络波动/API 变更），还有下一个平台
                logger.debug("平台 %s 歌词搜索异常: %s", provider.name, e)
                continue
            if result:
                lrc_text, song_info = result
                if lrc_text and _has_timestamps(lrc_text):
                    return lrc_text, provider.name, asdict(song_info)

    return None


def search_song_info(
    title: str,
    artist: str = "",
    providers: list[str] | tuple[str, ...] | None = None,
) -> Optional[dict]:
    """
    仅搜索歌曲名称、歌手以及专辑信息和封面 URL（不需要歌词）。

    返回: {"album": str, "cover_url": str, "matched_title": str, "matched_artist": str} 或 None
    """
    if not title:
        return None

    for provider in _resolve_providers(providers, for_info=True):
        try:
            info = provider.search_info(title, artist)
        except Exception as e:
            logger.debug("平台 %s 信息搜索异常: %s", provider.name, e)
            continue
        if info and not info.is_empty():
            return asdict(info)

    return None


def download_cover(cover_url: str) -> bytes | None:
    """下载封面图片，按域名自动加 Referer 绕过 CDN 防盗链；失败返回 None"""
    if not cover_url:
        return None

    headers = {}
    for domain, referer in _COVER_REFERERS.items():
        if domain in cover_url:
            headers["Referer"] = referer
            break

    try:
        resp = requests.get(cover_url, headers=headers, timeout=COVER_DOWNLOAD_TIMEOUT)
        if resp.status_code == 200 and len(resp.content) > COVER_MIN_BYTES:
            return resp.content
        logger.debug("封面响应无效（status=%s, bytes=%d）: %s",
                     resp.status_code, len(resp.content), cover_url)
    except Exception as e:
        logger.debug("封面下载失败 %s: %s", cover_url, e)
    return None


# ── Provider 抽象 ───────────────────────────────────────────────────────────


class LyricsProvider(ABC):
    """歌词平台接口：搜索同步歌词 + 搜索歌曲信息（可选）"""

    name: str = ""
    supports_info: bool = True

    @abstractmethod
    def search_lyrics(
        self, title: str, artist: str, synced_only: bool = True
    ) -> Optional[tuple[str, SongInfo]]:
        """搜索歌词，返回 (lrc_text, SongInfo) 或 None"""

    def search_info(self, title: str, artist: str) -> Optional[SongInfo]:
        """搜索专辑/封面信息（supports_info=False 的平台不实现）"""
        return None


def _resolve_providers(
    names: list[str] | tuple[str, ...] | None, *, for_info: bool
) -> list[LyricsProvider]:
    """
    解析平台列表：
    - None → 按 config.LYRICS_PROVIDERS 优先级顺序取全部
    - 显式列表 → 过滤未知名后按给定顺序
    - for_info=True 时跳过不支持信息搜索的平台（如 lrclib）
    """
    ordered = names if names is not None else LYRICS_PROVIDERS
    result = []
    for name in ordered:
        provider = _PROVIDERS.get(name)
        if provider is None:
            continue
        if for_info and not provider.supports_info:
            continue
        result.append(provider)
    return result


def _syncedlyrics_search(
    provider_name: str, title: str, artist: str, synced_only: bool
) -> Optional[str]:
    """通过 syncedlyrics 库搜索歌词（lrclib / NetEase 共用）"""
    search_term = f"{artist} {title}".strip() if artist else title
    try:
        return syncedlyrics.search(
            search_term, synced_only=synced_only, providers=[provider_name]
        )
    except Exception as e:
        logger.debug("syncedlyrics(%s) 搜索失败: %s", provider_name, e)
        return None


# ── QQ 音乐 ─────────────────────────────────────────────────────────────────


class QQMusicProvider(LyricsProvider):
    name = "QQMusic"

    _SEARCH_URL = "https://c.y.qq.com/soso/fcgi-bin/client_search_cp"
    _LYRIC_URL = "https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg"
    _HEADERS = {"Referer": "https://y.qq.com", "User-Agent": _UA}

    def search_lyrics(
        self, title: str, artist: str, synced_only: bool = True
    ) -> Optional[tuple[str, SongInfo]]:
        # QQ 接口不区分同步/非同步歌词，synced_only 参数忽略（与原实现一致）
        try:
            for song in self._search_songs(title, artist, limit=5):
                matched = self._match(song, title, artist)
                if not matched:
                    continue
                song_mid = song.get("songmid", "")
                if not song_mid:
                    continue
                lyric = self._fetch_lyric(song_mid)
                info = self._build_info(song, *matched)
                if lyric and _has_timestamps(lyric):
                    return lyric, info
                return None
        except Exception as e:
            logger.debug("QQ音乐歌词搜索失败: %s", e)
        return None

    def search_info(self, title: str, artist: str) -> Optional[SongInfo]:
        try:
            for song in self._search_songs(title, artist, limit=3):
                matched = self._match(song, title, artist)
                if not matched:
                    continue
                return self._build_info(song, *matched)
        except Exception as e:
            logger.debug("QQ音乐信息搜索失败: %s", e)
        return None

    def _search_songs(self, title: str, artist: str, limit: int) -> list[dict]:
        url = (
            f"{self._SEARCH_URL}"
            f"?w={requests.utils.quote(title + ' ' + artist)}"
            f"&format=json&n={limit}"
        )
        resp = requests.get(url, headers=self._HEADERS, timeout=HTTP_TIMEOUT)
        return resp.json().get("data", {}).get("song", {}).get("list", [])

    @staticmethod
    def _match(song: dict, title: str, artist: str) -> tuple[str, str] | None:
        """校验匹配，返回 (歌名, 歌手)；不匹配返回 None"""
        song_name = song.get("songname", "")
        singers = " ".join(s.get("name", "") for s in song.get("singer", []))
        if not _is_match(title, song_name, artist, singers):
            return None
        return song_name, singers

    def _fetch_lyric(self, song_mid: str) -> str:
        url = f"{self._LYRIC_URL}?songmid={song_mid}&format=json&nobase64=1"
        resp = requests.get(url, headers=self._HEADERS, timeout=HTTP_TIMEOUT)
        return resp.json().get("lyric", "")

    @staticmethod
    def _build_info(song: dict, song_name: str, singers: str) -> SongInfo:
        album_mid = song.get("albummid", "")
        cover_url = (
            f"https://y.qq.com/music/photo_new/T002R300x300M000{album_mid}.jpg"
            if album_mid else ""
        )
        return SongInfo(
            album=song.get("albumname", ""),
            cover_url=cover_url,
            matched_title=song_name,
            matched_artist=singers,
        )


# ── 酷狗音乐 ────────────────────────────────────────────────────────────────


class KugouProvider(LyricsProvider):
    name = "Kugou"

    _HEADERS = {"User-Agent": _UA}

    def search_lyrics(
        self, title: str, artist: str, synced_only: bool = True
    ) -> Optional[tuple[str, SongInfo]]:
        # 酷狗接口不区分同步/非同步歌词，synced_only 参数忽略（与原实现一致）
        try:
            for song in self._search_songs(title, artist, limit=5):
                matched = self._match(song, title, artist)
                if not matched:
                    continue
                song_hash = song.get("FileHash", "")
                if not song_hash:
                    continue
                lyric = self._fetch_lyric(song_hash)
                if lyric is None:
                    continue  # 无候选歌词，尝试下一首
                info = self._build_info(song, *matched)
                if lyric and _has_timestamps(lyric):
                    return lyric, info
                return None
        except Exception as e:
            logger.debug("酷狗歌词搜索失败: %s", e)
        return None

    def search_info(self, title: str, artist: str) -> Optional[SongInfo]:
        try:
            for song in self._search_songs(title, artist, limit=3):
                matched = self._match(song, title, artist)
                if not matched:
                    continue
                return self._build_info(song, *matched)
        except Exception as e:
            logger.debug("酷狗信息搜索失败: %s", e)
        return None

    def _search_songs(self, title: str, artist: str, limit: int) -> list[dict]:
        search_kw = f"{artist} {title}".strip()
        url = (
            "https://songsearch.kugou.com/song_search_v2"
            f"?keyword={requests.utils.quote(search_kw)}&page_size={limit}"
        )
        resp = requests.get(url, headers=self._HEADERS, timeout=HTTP_TIMEOUT)
        return resp.json().get("data", {}).get("lists", [])

    @staticmethod
    def _match(song: dict, title: str, artist: str) -> tuple[str, str] | None:
        """校验匹配（去除搜索结果中的 <em> 高亮标签），返回 (歌名, 歌手) 或 None"""
        song_name = song.get("SongName", "").replace("<em>", "").replace("</em>", "")
        singer = song.get("SingerName", "").replace("<em>", "").replace("</em>", "")
        if not _is_match(title, song_name, artist, singer):
            return None
        return song_name, singer

    def _fetch_lyric(self, song_hash: str) -> str | None:
        """两步获取歌词：hash → 候选 id/key → 下载 base64 内容；无候选返回 None"""
        lrc_url = (
            "https://krcs.kugou.com/search"
            f"?ver=1&man=yes&client=mobi&hash={song_hash}"
        )
        lrc_resp = requests.get(lrc_url, headers=self._HEADERS, timeout=HTTP_TIMEOUT)
        lrc_data = lrc_resp.json()

        candidates = lrc_data.get("candidates") or [{}]
        lyric_id = candidates[0].get("id", "")
        lyric_key = candidates[0].get("accesskey", "")
        if not lyric_id or not lyric_key:
            return None

        content_url = (
            "https://krcs.kugou.com/download"
            f"?ver=1&client=mobi&id={lyric_id}&accesskey={lyric_key}"
        )
        content_resp = requests.get(
            content_url, headers=self._HEADERS, timeout=HTTP_TIMEOUT
        )
        content_b64 = content_resp.json().get("content", "")
        if not content_b64:
            return ""
        return base64.b64decode(content_b64).decode("utf-8", errors="ignore")

    @staticmethod
    def _build_info(song: dict, song_name: str, singer: str) -> SongInfo:
        album_id = song.get("AlbumID", "")
        cover_url = (
            f"https://imge.kugou.com/stdmusic/150/{album_id}.jpg" if album_id else ""
        )
        return SongInfo(
            album=song.get("AlbumName", ""),
            cover_url=cover_url,
            matched_title=song_name,
            matched_artist=singer,
        )


# ── 网易云音乐 ──────────────────────────────────────────────────────────────


class NetEaseProvider(LyricsProvider):
    name = "NetEase"

    def search_lyrics(
        self, title: str, artist: str, synced_only: bool = True
    ) -> Optional[tuple[str, SongInfo]]:
        # 歌词走 syncedlyrics，专辑/封面走自建 API（与原实现一致）
        lrc = _syncedlyrics_search("NetEase", title, artist, synced_only)
        if not lrc:
            return None
        info = self.search_info(title, artist) or SongInfo()
        return lrc, info

    def search_info(self, title: str, artist: str) -> Optional[SongInfo]:
        try:
            search_kw = f"{artist} {title}".strip()
            url = (
                "https://music.163.com/api/search/get/web"
                f"?s={requests.utils.quote(search_kw)}&type=1&limit=5"
            )
            headers = {"Referer": "https://music.163.com", "User-Agent": _UA}
            resp = requests.post(url, headers=headers, timeout=HTTP_TIMEOUT)
            songs = resp.json().get("result", {}).get("songs", [])
            for song in songs:
                song_name = song.get("name", "")
                singers = " ".join(s.get("name", "") for s in song.get("artists", []))
                if not _is_match(title, song_name, artist, singers):
                    continue
                album = song.get("album", {})
                return SongInfo(
                    album=album.get("name", ""),
                    cover_url=album.get("picUrl", ""),
                    matched_title=song_name,
                    matched_artist=singers,
                )
        except Exception as e:
            logger.debug("网易云信息搜索失败: %s", e)
        return None


# ── lrclib ──────────────────────────────────────────────────────────────────


class LrcLibProvider(LyricsProvider):
    name = "lrclib"
    supports_info = False  # lrclib 不提供专辑/封面信息

    def search_lyrics(
        self, title: str, artist: str, synced_only: bool = True
    ) -> Optional[tuple[str, SongInfo]]:
        lrc = _syncedlyrics_search("lrclib", title, artist, synced_only)
        if not lrc:
            return None
        return lrc, SongInfo()


# ── 平台注册表（搜索优先级顺序由 config.LYRICS_PROVIDERS 决定）────────────────

_PROVIDERS: dict[str, LyricsProvider] = {
    "QQMusic": QQMusicProvider(),
    "Kugou": KugouProvider(),
    "NetEase": NetEaseProvider(),
    "lrclib": LrcLibProvider(),
}


# ── 工具函数 ────────────────────────────────────────────────────────────────


def _has_timestamps(lrc_text: str) -> bool:
    """检查歌词是否包含 LRC 时间戳格式 [mm:ss.xx]"""
    pattern = re.compile(r"\[\d{1,3}:\d{2}(?:\.\d{1,3})?\]")
    return bool(pattern.search(lrc_text))


def _normalize(text: str) -> str:
    """标准化文本：去除括号、特殊符号、多余空格，统一小写"""
    text = text.lower().strip()
    text = re.sub(r"[\(（\[【].*?[\)）\]】]", "", text)
    text = re.sub(r"[^\w一-鿿\s]", "", text)
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
