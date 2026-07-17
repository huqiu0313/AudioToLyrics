"""处理流程编排：串联歌词搜索、人声分离、语音识别、LRC 输出"""

from pathlib import Path
from typing import Callable

import zhconv

from utils.audio_info import extract_info
from core.lyrics_search import search_lyrics
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
    处理单个音频文件的完整流程。

    流程：
    1. 提取歌曲信息（标题/艺术家）
    2. 联网搜索官方歌词
    3. 若找到 → 直接保存 LRC（跳过分离+识别）
    4. 若未找到 → Demucs 分离人声 → Whisper 识别 → 生成 LRC

    参数:
        audio_path: 音频文件路径
        progress_callback: (percent, message) 进度回调
        config: 配置字典，可包含：
            - whisper_model: Whisper 模型名
            - demucs_model: Demucs 模型名
            - providers: 歌词搜索平台列表

    返回:
        结果摘要字符串
    """
    cfg = config or {}
    whisper_model = cfg.get("whisper_model", "base")
    demucs_model = cfg.get("demucs_model", "htdemucs")
    providers = cfg.get("providers", None)

    # Step 1: 提取歌曲信息
    progress_callback(5, "正在读取歌曲信息...")
    title, artist, alternates = extract_info(audio_path)
    lrc_path = get_lrc_path(audio_path)
    filename = Path(audio_path).name

    # Step 2: 联网搜索歌词（若文件名解析不确定，尝试两种 title/artist 顺序）
    progress_callback(15, f"正在联网搜索歌词: {title} - {artist}")
    search_result = search_lyrics(title, artist, providers=providers)

    if not search_result:
        for alt_title, alt_artist in alternates:
            progress_callback(15, f"尝试备选: {alt_title} - {alt_artist}")
            search_result = search_lyrics(alt_title, alt_artist, providers=providers)
            if search_result:
                title, artist = alt_title, alt_artist
                break

    if search_result:
        # 找到官方歌词，繁转简后直接保存
        official_lrc, source = search_result
        official_lrc = zhconv.convert(official_lrc, "zh-cn")
        progress_callback(80, f"找到官方歌词（来源: {source}），正在保存...")
        save_lrc(official_lrc, lrc_path)
        progress_callback(100, f"完成（官方歌词 · {source}）: {filename}")
        return f"完成（官方歌词 · {source}）→ {lrc_path}"

    # Step 3: 未找到官方歌词，使用 Whisper
    progress_callback(25, "未找到官方歌词，准备语音识别...")

    # 人声分离
    progress_callback(35, "正在使用 Demucs 分离人声...")
    vocals_path = separate_vocals(audio_path, model_name=demucs_model)
    progress_callback(55, "人声分离完成")

    # Whisper 识别
    progress_callback(60, f"正在使用 Whisper ({whisper_model}) 识别歌词...")
    segments = transcribe(vocals_path, model_name=whisper_model)

    if not segments:
        progress_callback(100, f"未识别到任何歌词: {filename}")
        return f"未识别到歌词: {filename}"

    # 繁体转简体
    for seg in segments:
        seg["text"] = zhconv.convert(seg["text"], "zh-cn")

    # Step 4: 生成 LRC 并保存
    progress_callback(85, "正在生成 LRC 文件...")
    lrc_content = build_lrc_from_whisper(segments, title=title, artist=artist)
    save_lrc(lrc_content, lrc_path)
    progress_callback(95, f"LRC 已保存: {lrc_path}")

    return f"完成（Whisper 识别 · {whisper_model}）→ {lrc_path}"
