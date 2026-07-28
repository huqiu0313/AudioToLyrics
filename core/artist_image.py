"""歌手头像扫描：遍历音乐库提取歌手信息，联网搜索并下载歌手头像"""

import os
import re
from pathlib import Path
from typing import Callable

import requests
from mutagen import File as MutagenFile

from config import SUPPORTED_FORMATS
from core.internet_search import search_artist_image_url


# 合作歌手分隔符正则
_ARTIST_SPLIT_RE = re.compile(
    r"\s*(?:/|&|、|,|，|feat\.|ft\.|with)\s*", re.IGNORECASE
)


def scan_artists(music_dir: str) -> set[str]:
    """
    遍历目录下所有音频文件，提取歌手名集合。

    - 读取 artist tag
    - 拆分合作歌手（按 /、&、、,、feat.、ft.、with 分割）
    - 去除空白和重复
    """
    artists: set[str] = set()
    music_path = Path(music_dir)

    for root, _, files in os.walk(music_path):
        for name in files:
            if Path(name).suffix.lower() not in SUPPORTED_FORMATS:
                continue
            filepath = os.path.join(root, name)
            try:
                audio = MutagenFile(filepath, easy=True)
                if audio is None:
                    continue
                artist_tag = audio.get("artist", [""])[0] if audio.get("artist") else ""
                if not artist_tag:
                    continue
                # 拆分合作歌手
                parts = _ARTIST_SPLIT_RE.split(artist_tag)
                for part in parts:
                    part = part.strip()
                    if part:
                        artists.add(part)
            except Exception:
                continue

    return artists


def fetch_artist_images(
    music_dir: str,
    progress_callback: Callable[[int, str], None] | None = None,
) -> dict:
    """
    扫描音乐库中的歌手，联网搜索并下载头像。

    保存到 {music_dir}/ArtistImage/{歌手名}.jpg，已存在则跳过。

    返回:
        {"success": [...], "failed": [...], "skipped": [...]}
    """
    result = {"success": [], "failed": [], "skipped": []}

    if progress_callback:
        progress_callback(0, "正在扫描音乐库中的歌手信息...")

    artists = scan_artists(music_dir)
    if not artists:
        if progress_callback:
            progress_callback(100, "未找到任何歌手信息")
        return result

    # 创建输出目录
    img_dir = Path(music_dir) / "ArtistImage"
    img_dir.mkdir(parents=True, exist_ok=True)

    total = len(artists)
    artist_list = sorted(artists)

    for i, artist_name in enumerate(artist_list):
        percent = int((i + 1) / total * 100)

        # 检查是否已存在
        safe_name = _sanitize_filename(artist_name)
        img_path = img_dir / f"{safe_name}.jpg"
        if img_path.exists():
            result["skipped"].append(artist_name)
            if progress_callback:
                progress_callback(percent, f"[{i+1}/{total}] 已存在，跳过: {artist_name}")
            continue

        if progress_callback:
            progress_callback(percent, f"[{i+1}/{total}] 正在搜索: {artist_name}")

        # 搜索头像 URL
        try:
            image_url = search_artist_image_url(artist_name)
            if not image_url:
                result["failed"].append(artist_name)
                continue

            # 下载图片
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            if "qq.com" in image_url:
                headers["Referer"] = "https://y.qq.com"
            elif "163.com" in image_url:
                headers["Referer"] = "https://music.163.com"

            resp = requests.get(image_url, headers=headers, timeout=15)
            if resp.status_code == 200 and len(resp.content) > 500:
                img_path.write_bytes(resp.content)
                result["success"].append(artist_name)
            else:
                result["failed"].append(artist_name)
        except Exception:
            result["failed"].append(artist_name)

    if progress_callback:
        msg = (
            f"完成 - 成功: {len(result['success'])}, "
            f"跳过: {len(result['skipped'])}, "
            f"失败: {len(result['failed'])}"
        )
        progress_callback(100, msg)

    return result


def _sanitize_filename(name: str) -> str:
    """清理文件名中的非法字符"""
    return re.sub(r'[<>:"/\\|?*]', "_", name).strip()
