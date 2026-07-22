"""处理流程编排：视频转音频 → 歌词搜索 → tag写入 → 人声分离 → 语音识别 → LRC 输出"""

import requests
from pathlib import Path
from typing import Callable

import zhconv

from utils.audio_info import extract_info
from core.internet_search import search_lyrics, search_song_info
from core.video_converter import is_video, convert_to_audio
from core.tag_writer import write_tags
from core.separator import separate_vocals
from core.transcriber import transcribe
from core.lrc_builder import (
    build_lrc_from_whisper,
    save_lrc,
    get_lrc_path,
)


def process_file(
    audio_path: str,
    progress_callback: Callable[[int, str], None],
    config: dict | None = None,
) -> str:
    """
    处理单个音频/视频文件的完整流程。

    流程：
    0. 若为视频且启用了自动转换 → 无损提取音轨
    1. 提取歌曲信息（标题/艺术家）
    2. 联网搜索官方歌词 + 专辑/封面
    3. 写入 tag（标题/艺术家/专辑/封面）
    4. 若找到歌词 → 直接保存 LRC
    5. 若未找到 → 检查是否启用 Demucs/Whisper → 分离 + 识别 → 生成 LRC
    """
    cfg = config or {}
    whisper_model = cfg.get("whisper_model", "base")
    demucs_model = cfg.get("demucs_model", "htdemucs")
    providers = cfg.get("providers", None)
    auto_convert = cfg.get("auto_convert_video", True)
    use_demucs = cfg.get("use_demucs", False)
    use_whisper = cfg.get("use_whisper", False)

    # ── Step 0: 视频转音频 ────────────────────────────────────────────────
    if is_video(audio_path):
        if auto_convert:
            progress_callback(3, f"检测到视频文件，正在提取音轨...")
            try:
                audio_path = convert_to_audio(audio_path)
                progress_callback(8, f"音轨提取完成: {Path(audio_path).name}")
            except Exception as e:
                progress_callback(100, f"视频转音频失败: {e}")
                return f"视频转音频失败: {e}"
        else:
            return f"跳过视频文件（未启用自动转换）: {Path(audio_path).name}"

    # ── Step 1: 提取歌曲信息 ──────────────────────────────────────────────
    progress_callback(10, "正在读取歌曲信息...")
    title, artist, alternates = extract_info(audio_path)
    lrc_path = get_lrc_path(audio_path)
    filename = Path(audio_path).name

    # ── Step 2: 联网搜索歌词 + 专辑/封面 ──────────────────────────────────
    progress_callback(18, f"正在联网搜索歌词: {title} - {artist}")
    search_result = search_lyrics(title, artist, providers=providers)

    if not search_result:
        for alt_title, alt_artist in alternates:
            progress_callback(18, f"尝试备选: {alt_title} - {alt_artist}")
            search_result = search_lyrics(alt_title, alt_artist, providers=providers)
            if search_result:
                title, artist = alt_title, alt_artist
                break

    # 提取搜索结果中的歌曲信息
    song_info: dict = {}
    official_lrc = ""
    source = ""
    if search_result:
        official_lrc, source, song_info = search_result
        song_info = song_info or {}

    # 若歌词搜索未返回专辑/封面，独立搜索一次
    if not song_info.get("album") and not song_info.get("cover_url") \
            and not song_info.get("matched_title"):
        progress_callback(30, "正在搜索专辑信息...")
        extra_info = search_song_info(title, artist, providers=providers)
        if extra_info:
            song_info.update({k: v for k, v in extra_info.items() if v})

    # 用联网匹配到的歌曲名/歌手名覆盖（比文件名解析更准确）
    tag_title = song_info.get("matched_title") or title
    tag_artist = song_info.get("matched_artist") or artist

    # ── Step 3: 下载封面 + 写入 tag ──────────────────────────────────────
    cover_bytes = None
    cover_url = song_info.get("cover_url", "")
    if cover_url:
        progress_callback(35, "正在下载专辑封面...")
        try:
            # 根据域名自动加 Referer，绕过 CDN 防盗链
            headers = {}
            if "y.qq.com" in cover_url or "qq.com" in cover_url:
                headers["Referer"] = "https://y.qq.com"
            elif "kugou.com" in cover_url:
                headers["Referer"] = "https://www.kugou.com"
            elif "163.com" in cover_url:
                headers["Referer"] = "https://music.163.com"
            resp = requests.get(cover_url, headers=headers, timeout=10)
            if resp.status_code == 200 and len(resp.content) > 500:
                cover_bytes = resp.content
        except Exception:
            pass

    album = song_info.get("album", "")
    progress_callback(38, "正在写入音频标签...")
    tag_result = write_tags(
        audio_path,
        title=tag_title,
        artist=tag_artist,
        album=album,
        cover_bytes=cover_bytes,
    )
    written = [k for k, v in tag_result.items() if v]
    if written:
        progress_callback(40, f"已写入标签: {', '.join(written)}")

    # ── Step 4: 保存官方歌词 ──────────────────────────────────────────────
    if official_lrc:
        official_lrc = zhconv.convert(official_lrc, "zh-cn")
        progress_callback(85, f"找到官方歌词（来源: {source}），正在保存...")
        save_lrc(official_lrc, lrc_path)
        progress_callback(100, f"完成（官方歌词 · {source}）: {filename}")
        return f"完成（官方歌词 · {source}）→ {lrc_path}"

    # ── Step 5: 未找到官方歌词 → 可选 Demucs + Whisper ───────────────────
    if not use_demucs and not use_whisper:
        msg = "未找到官方歌词，且未启用语音识别（Demucs/Whisper），跳过该文件"
        progress_callback(100, msg)
        return f"{msg}: {filename}"

    progress_callback(45, "未找到官方歌词，准备语音识别...")

    # 人声分离（仅在启用时执行）
    vocals_path = audio_path
    if use_demucs:
        progress_callback(50, f"正在使用 Demucs ({demucs_model}) 分离人声...")
        vocals_path = separate_vocals(audio_path, model_name=demucs_model)
        progress_callback(60, "人声分离完成")
    else:
        progress_callback(50, "未启用 Demucs，使用原始音频进行识别...")

    # Whisper 识别
    if not use_whisper:
        msg = "未启用 Whisper，无法进行语音识别，跳过该文件"
        progress_callback(100, msg)
        return f"{msg}: {filename}"

    progress_callback(65, f"正在使用 Whisper ({whisper_model}) 识别歌词...")
    segments = transcribe(vocals_path, model_name=whisper_model)

    if not segments:
        progress_callback(100, f"未识别到任何歌词: {filename}")
        return f"未识别到歌词: {filename}"

    # 繁体转简体
    for seg in segments:
        seg["text"] = zhconv.convert(seg["text"], "zh-cn")

    # 生成 LRC 并保存
    progress_callback(90, "正在生成 LRC 文件...")
    lrc_content = build_lrc_from_whisper(segments, title=title, artist=artist)
    save_lrc(lrc_content, lrc_path)
    progress_callback(95, f"LRC 已保存: {lrc_path}")

    return f"完成（Whisper 识别 · {whisper_model}）→ {lrc_path}"
