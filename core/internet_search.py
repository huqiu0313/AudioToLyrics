"""联网搜索：歌词、专辑、封面、歌曲名、歌手名：支持 lrclib、网易云、QQ音乐、酷狗"""

import re
import base64
import requests
from typing import Optional
from difflib import SequenceMatcher

import syncedlyrics
import zhconv


# 标题/歌手匹配的最低相似度阈值
_MIN_TITLE_SIMILARITY = 0.8
_MIN_ARTIST_SIMILARITY = 0.7


# 歌手分隔符正则
_ARTIST_SPLIT_RE = re.compile(
    r"\s*(?:/|&|、|,|，|feat\.|ft\.|with)\s*", re.IGNORECASE
)

# LRC 时间戳正则（预编译）
_TIMESTAMP_RE = re.compile(r"\[\d{1,3}:\d{2}(?:\.\d{1,3})?\]")

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
    search_term = f"{title} {artist}".strip() if artist else title

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


def _qq_music_find_song(title: str, artist: str, limit: int = 5) -> Optional[dict]:
    """QQ音乐搜索并返回第一个匹配的歌曲原始数据，未匹配返回 None"""
    url = (
        "https://c.y.qq.com/soso/fcgi-bin/client_search_cp"
        f"?w={requests.utils.quote(title + ' ' + artist)}"
        f"&format=json&n={limit}"
    )
    headers = {"Referer": "https://y.qq.com", "User-Agent": _UA}
    resp = requests.get(url, headers=headers, timeout=8)
    songs = resp.json().get("data", {}).get("song", {}).get("list", [])

    for song in songs:
        song_name = song.get("songname", "")
        singers = "/".join(s.get("name", "") for s in song.get("singer", []))
        if not _is_match(title, song_name, artist, singers):
            continue
        return song
    return None


def _qq_music_song_info(song: dict) -> dict:
    """从 QQ音乐 song 对象提取专辑/封面/歌曲名/歌手名"""
    song_name = song.get("songname", "")
    singers = "/".join(s.get("name", "") for s in song.get("singer", []))
    album_mid = song.get("albummid", "")
    cover_url = f"https://y.qq.com/music/photo_new/T002R300x300M000{album_mid}.jpg" if album_mid else ""
    return {
        "album": song.get("albumname", ""),
        "cover_url": cover_url,
        "matched_title": song_name,
        "matched_artist": singers,
    }


def _search_qq_music(title: str, artist: str) -> Optional[tuple[str, dict]]:
    """从 QQ 音乐搜索歌词 + 专辑/封面"""
    try:
        song = _qq_music_find_song(title, artist)
        if not song:
            return None
        song_mid = song.get("songmid", "")
        if not song_mid:
            return None

        headers = {"Referer": "https://y.qq.com", "User-Agent": _UA}
        lrc_url = (
            "https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg"
            f"?songmid={song_mid}&format=json&nobase64=1"
        )
        lyric = requests.get(lrc_url, headers=headers, timeout=8).json().get("lyric", "")
        song_info = _qq_music_song_info(song)

        if lyric and _has_timestamps(lyric):
            return lyric, song_info
        return None
    except Exception:
        return None


def _qq_music_info(title: str, artist: str) -> Optional[dict]:
    """仅从 QQ 音乐获取专辑/封面信息"""
    try:
        song = _qq_music_find_song(title, artist, limit=3)
        return _qq_music_song_info(song) if song else None
    except Exception:
        return None


# ── 酷狗音乐 ────────────────────────────────────────────────────────────────


def _kugou_find_song(title: str, artist: str, limit: int = 5) -> Optional[dict]:
    """酷狗搜索并返回第一个匹配的歌曲原始数据，未匹配返回 None"""
    search_kw = f"{title} {artist}".strip()
    url = (
        "https://songsearch.kugou.com/song_search_v2"
        f"?keyword={requests.utils.quote(search_kw)}&page_size={limit}"
    )
    resp = requests.get(url, headers={"User-Agent": _UA}, timeout=8)
    songs = resp.json().get("data", {}).get("lists", [])

    for song in songs:
        song_name = song.get("SongName", "").replace("<em>", "").replace("</em>", "")
        singer = song.get("SingerName", "").replace("<em>", "").replace("</em>", "")
        if not _is_match(title, song_name, artist, singer):
            continue
        return song
    return None


def _kugou_song_info(song: dict) -> dict:
    """从酷狗 song 对象提取专辑/封面/歌曲名/歌手名"""
    song_name = song.get("SongName", "").replace("<em>", "").replace("</em>", "")
    singer = song.get("SingerName", "").replace("<em>", "").replace("</em>", "")
    album_id = song.get("AlbumID", "")
    cover_url = f"https://imge.kugou.com/stdmusic/150/{album_id}.jpg" if album_id else ""
    return {
        "album": song.get("AlbumName", ""),
        "cover_url": cover_url,
        "matched_title": song_name,
        "matched_artist": singer,
    }


def _search_kugou(title: str, artist: str) -> Optional[tuple[str, dict]]:
    """从酷狗音乐搜索歌词 + 专辑/封面"""
    try:
        song = _kugou_find_song(title, artist)
        if not song:
            return None
        song_hash = song.get("FileHash", "")
        if not song_hash:
            return None

        # 获取歌词
        lrc_resp = requests.get(
            f"https://krcs.kugou.com/search?ver=1&man=yes&client=mobi&hash={song_hash}",
            headers={"User-Agent": _UA}, timeout=8,
        ).json()
        candidates = lrc_resp.get("candidates", [{}])
        lyric_id = candidates[0].get("id", "")
        lyric_key = candidates[0].get("accesskey", "")
        if not lyric_id or not lyric_key:
            return None

        content_data = requests.get(
            f"https://krcs.kugou.com/download?ver=1&client=mobi&id={lyric_id}&accesskey={lyric_key}",
            headers={"User-Agent": _UA}, timeout=8,
        ).json()
        content_b64 = content_data.get("content", "")
        lyric = base64.b64decode(content_b64).decode("utf-8", errors="ignore") if content_b64 else ""

        song_info = _kugou_song_info(song)
        if lyric and _has_timestamps(lyric):
            return lyric, song_info
        return None
    except Exception:
        return None


def _kugou_info(title: str, artist: str) -> Optional[dict]:
    """仅从酷狗获取专辑/封面信息"""
    try:
        song = _kugou_find_song(title, artist, limit=3)
        return _kugou_song_info(song) if song else None
    except Exception:
        return None


# ── 网易云音乐 ──────────────────────────────────────────────────────────────


def _netease_info(title: str, artist: str) -> Optional[dict]:
    """从网易云获取专辑/封面信息"""
    try:
        search_kw = f"{title} {artist}".strip()
        url = (
            "https://music.163.com/api/search/get/web"
            f"?s={requests.utils.quote(search_kw)}&type=1&limit=5"
        )
        headers = {"Referer": "https://music.163.com", "User-Agent": _UA}
        resp = requests.post(url, headers=headers, timeout=8)
        songs = resp.json().get("result", {}).get("songs", [])
        for song in songs:
            song_name = song.get("name", "")
            singers = "/".join(s.get("name", "") for s in song.get("artists", []))
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


# ── 歌手头像搜索 ──────────────────────────────────────────────────────────────


def search_artist_image_url(artist_name: str) -> Optional[str]:
    """联网搜索歌手头像 URL（优先 QQ音乐，备选网易云）"""
    if not artist_name:
        return None
    return _qq_music_artist_image(artist_name) or _netease_artist_image(artist_name)


def _qq_music_artist_image(artist_name: str) -> Optional[str]:
    """从 QQ音乐搜索歌手头像"""
    try:
        url = (
            "https://c.y.qq.com/soso/fcgi-bin/client_search_cp"
            f"?w={requests.utils.quote(artist_name)}"
            "&format=json&n=1&remoteplace=txt.yqq.singer"
        )
        headers = {"Referer": "https://y.qq.com", "User-Agent": _UA}
        resp = requests.get(url, headers=headers, timeout=8)
        data = resp.json().get("data", {})

        # 优先从 singer 列表获取
        singers = data.get("singer", {}).get("list", [])
        if singers:
            singer_mid = singers[0].get("singer_mid", "")
            if singer_mid:
                return f"https://y.qq.com/music/photo_new/T001R300x300M000{singer_mid}.jpg"

        # 备选：从歌曲结果中提取歌手 mid
        songs = data.get("song", {}).get("list", [])
        for song in songs:
            for singer in song.get("singer", []):
                singer_mid = singer.get("mid", "")
                if singer_mid:
                    return f"https://y.qq.com/music/photo_new/T001R300x300M000{singer_mid}.jpg"
    except Exception:
        pass
    return None


def _netease_artist_image(artist_name: str) -> Optional[str]:
    """从网易云搜索歌手头像"""
    try:
        url = (
            "https://music.163.com/api/search/get/web"
            f"?s={requests.utils.quote(artist_name)}&type=100&limit=1"
        )
        headers = {"Referer": "https://music.163.com", "User-Agent": _UA}
        resp = requests.post(url, headers=headers, timeout=8)
        artists = resp.json().get("result", {}).get("artists", [])
        if artists:
            artist = artists[0]
            # 优先使用 img1v1Url（歌手头像），备选 picUrl
            img_url = artist.get("img1v1Url", "") or artist.get("picUrl", "")
            if img_url and "default" not in img_url:
                return img_url
    except Exception:
        pass
    return None


# ── 工具函数 ────────────────────────────────────────────────────────────────


def _has_timestamps(lrc_text: str) -> bool:
    """检查歌词是否包含 LRC 时间戳格式 [mm:ss.xx]"""
    return bool(_TIMESTAMP_RE.search(lrc_text))


def _normalize(text: str) -> str:
    """
    标准化文本用于比较：
    - 繁转简
    - 统一小写
    - 去除首尾空白和多余空格
    - 仅去除不影响语义的特殊符号（保留括号、字母、数字、中文）
    """
    text = zhconv.convert(text, "zh-cn")
    text = text.lower().strip()
    text = re.sub(r"[^\w\u4e00-\u9fff\s()（）\[\]【】]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _title_core(text: str) -> str:
    """提取歌曲标题的核心部分，去掉括号/分隔符后的后缀修饰。"""
    if not text:
        return ""
    normalized = _normalize(text)
    if not normalized:
        return ""
    for sep in ["(", "（", "[", "【", "-", "—", ":", "：", "/", "、", "."]:
        if sep in normalized:
            normalized = normalized.split(sep, 1)[0]
    return normalized.strip()


def _similarity(a: str, b: str) -> float:
    """计算两个字符串的相似度（0~1）"""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _split_artists(artist_str: str) -> list[str]:
    """将歌手字符串按分隔符拆分为列表，每个元素经过 normalize"""
    if not artist_str:
        return []
    parts = _ARTIST_SPLIT_RE.split(artist_str)
    return [_normalize(p) for p in parts if p.strip()]


def _artists_match(expected_artist: str, actual_artist: str) -> bool:
    """
    校验歌手是否匹配：
    - 拆分为多个歌手后，允许顺序不同
    - 对于 2 位歌手，要求两边都能各自匹配到对方，顺序可变
    - 对于 3 位及以上歌手，至少要有 2 位成功匹配
    - 单个歌手之间用相似度 >= _MIN_ARTIST_SIMILARITY 判定
    """
    expected_list = _split_artists(expected_artist)
    actual_list = _split_artists(actual_artist)

    if not expected_list or not actual_list:
        return True  # 缺少一方信息时不做歌手校验

    if len(expected_list) == 1:
        return any(_similarity(expected_list[0], act) >= _MIN_ARTIST_SIMILARITY for act in actual_list)
    if len(actual_list) == 1:
        return any(_similarity(exp, actual_list[0]) >= _MIN_ARTIST_SIMILARITY for exp in expected_list)

    if len(expected_list) == 2 and len(actual_list) == 2:
        return (
            _similarity(expected_list[0], actual_list[0]) >= _MIN_ARTIST_SIMILARITY
            and _similarity(expected_list[1], actual_list[1]) >= _MIN_ARTIST_SIMILARITY
        ) or (
            _similarity(expected_list[0], actual_list[1]) >= _MIN_ARTIST_SIMILARITY
            and _similarity(expected_list[1], actual_list[0]) >= _MIN_ARTIST_SIMILARITY
        )

    matched = 0
    for exp in expected_list:
        if any(_similarity(exp, act) >= _MIN_ARTIST_SIMILARITY for act in actual_list):
            matched += 1

    return matched >= 2


def _is_match(
    expected_title: str, actual_title: str,
    expected_artist: str = "", actual_artist: str = "",
) -> bool:
    """
    校验搜索结果的歌曲是否与目标匹配：
    - 以歌曲标题的核心部分为准，允许括号/后缀修饰信息（如 Live、Remix）
    - 歌手：多歌手时允许顺序不同，但不允许多/少/不同
    """
    expected_core = _title_core(expected_title)
    actual_core = _title_core(actual_title)

    if expected_core and actual_core:
        if expected_core == actual_core:
            title_ok = True
        else:
            title_ok = _similarity(expected_core, actual_core) >= 0.7
    else:
        title_ok = bool(_normalize(expected_title) and _normalize(actual_title)) and _similarity(
            _normalize(expected_title), _normalize(actual_title)
        ) >= 0.7

    if not title_ok:
        return False
    if expected_artist and actual_artist:
        if not _artists_match(expected_artist, actual_artist):
            return False
    return True
