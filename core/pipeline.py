"""处理流程编排：加密解密 → 视频转音频 → 歌词搜索 → tag写入 → 人声分离 → 语音识别 → LRC 输出

process_file 为唯一入口（编排器），各阶段拆分为独立的步骤函数。
"""

import os
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import zhconv

from utils.audio_info import extract_info
from utils.process import ProcessCancelledError
from core.internet_search import download_cover, search_lyrics, search_song_info
from core.decryptor import is_encrypted, decrypt_audio
from core.processing_config import ProcessingConfig
from core.video_converter import is_video, convert_to_audio
from core.tag_writer import write_tags
from core.separator import separate_vocals
from core.transcriber import transcribe
from core.lrc_builder import (
    build_lrc_from_whisper,
    save_lrc,
    get_lrc_path,
)


class _Pct:
    """编排进度百分比（仅 process_file 及各步骤函数使用）"""
    DECRYPT = 2             # 正在解密
    DECRYPT_DONE = 7        # 解密完成
    SOURCE_DELETED = 8      # 源文件已删除（解密/转码后）
    CONVERT = 3             # 正在提取音轨
    CONVERT_DONE = 8        # 音轨提取完成
    CONVERT_SOURCE_DELETED = 9
    READ_INFO = 10          # 正在读取歌曲信息
    SEARCH = 18             # 正在联网搜索歌词（含备选重试）
    SEARCH_INFO = 30        # 正在搜索专辑信息
    COVER = 35              # 正在下载专辑封面
    TAGS = 38               # 正在写入音频标签
    TAGS_DONE = 40          # 标签写入完成
    PREPARE_ASR = 45        # 准备语音识别
    SEPARATE = 50           # 正在分离人声 / 跳过分离
    SEPARATE_DONE = 60      # 人声分离完成
    TRANSCRIBE = 65         # 正在 Whisper 识别
    SAVE_OFFICIAL = 85      # 正在保存官方歌词
    BUILD_LRC = 90          # 正在生成 LRC
    LRC_SAVED = 95          # LRC 已保存
    DONE = 100


class _SkipFile(Exception):
    """文件被跳过（非错误，消息直接作为处理结果返回）"""


@dataclass
class _SearchOutcome:
    """联网搜索阶段的产出"""
    title: str
    artist: str
    official_lrc: str = ""
    source: str = ""
    song_info: dict = field(default_factory=dict)


def process_file(
    audio_path: str,
    progress_callback: Callable[[int, str], None],
    config: dict | None = None,
    cancel_event: threading.Event | None = None,
) -> str:
    """
    处理单个音频/视频文件的完整流程。

    流程：
    1. 若为加密音频 → 解密（首次使用自动下载解密工具）
    2. 若为视频且启用了自动转换 → 无损提取音轨
    3. 提取歌曲信息（标题/艺术家）
    4. 联网搜索官方歌词 + 专辑/封面
    5. 写入 tag（标题/艺术家/专辑/封面）
    6. 若找到歌词 → 直接保存 LRC
    7. 若未找到 → 检查是否启用 Demucs/Whisper → 分离 + 识别 → 生成 LRC

    参数:
        cancel_event: 可选的取消事件；set 后阶段边界提前返回"已取消"，
                      正在运行的解密/转码/分离子进程会被终止
                      （Whisper 推理为 C++ 层调用，不可中断）

    返回结果描述文本（供批处理汇总显示）。
    """
    cfg = ProcessingConfig.from_dict(config)
    filename = Path(audio_path).name

    def _cancelled() -> bool:
        return cancel_event is not None and cancel_event.is_set()

    try:
        audio_path = _step_decrypt(audio_path, cfg, progress_callback, cancel_event)
        if _cancelled():
            raise ProcessCancelledError
        audio_path = _step_convert_video(audio_path, cfg, progress_callback, cancel_event)
    except _SkipFile as e:
        return str(e)
    except ProcessCancelledError:
        return f"已取消: {filename}"
    except Exception as e:
        progress_callback(_Pct.DONE, str(e))
        return str(e)

    if _cancelled():
        return f"已取消: {filename}"

    progress_callback(_Pct.READ_INFO, "正在读取歌曲信息...")
    title, artist, alternates = extract_info(audio_path)
    lrc_path = get_lrc_path(audio_path)

    outcome = _step_search(title, artist, alternates, cfg, progress_callback)

    if _cancelled():
        return f"已取消: {filename}"

    _step_write_tags(audio_path, outcome, progress_callback)

    if outcome.official_lrc:
        return _step_save_official_lrc(outcome, lrc_path, filename, progress_callback)

    try:
        return _step_recognize(
            audio_path, outcome, cfg, lrc_path, filename, progress_callback, cancel_event
        )
    except ProcessCancelledError:
        return f"已取消: {filename}"


# ── 步骤函数 ────────────────────────────────────────────────────────────────


def _step_decrypt(
    audio_path: str,
    cfg: ProcessingConfig,
    cb: Callable[[int, str], None],
    cancel_event: threading.Event | None,
) -> str:
    """加密音频解密（首次使用自动下载解密工具）；非加密文件原样返回"""
    if not is_encrypted(audio_path):
        return audio_path

    cb(_Pct.DECRYPT, "检测到加密音频，正在解密...")
    try:
        original_path = audio_path
        audio_path = decrypt_audio(
            audio_path,
            output_dir=cfg.decrypt_output_dir,
            progress_callback=cb,
            cancel_event=cancel_event,
        )
        cb(_Pct.DECRYPT_DONE, f"解密完成: {Path(audio_path).name}")
        # 若启用删除源文件，删除原加密文件
        if cfg.delete_source_after_convert and os.path.exists(original_path):
            os.remove(original_path)
            cb(_Pct.SOURCE_DELETED, f"已删除源文件: {Path(original_path).name}")
        return audio_path
    except ProcessCancelledError:
        raise
    except Exception as e:
        raise RuntimeError(f"加密音频解密失败: {e}") from e


def _step_convert_video(
    audio_path: str,
    cfg: ProcessingConfig,
    cb: Callable[[int, str], None],
    cancel_event: threading.Event | None,
) -> str:
    """视频文件无损提取音轨；非视频文件原样返回，未启用转换则跳过"""
    if not is_video(audio_path):
        return audio_path
    if not cfg.auto_convert_video:
        raise _SkipFile(f"跳过视频文件（未启用自动转换）: {Path(audio_path).name}")

    cb(_Pct.CONVERT, "检测到视频文件，正在提取音轨...")
    try:
        original_path = audio_path
        audio_path = convert_to_audio(audio_path, cancel_event=cancel_event)
        cb(_Pct.CONVERT_DONE, f"音轨提取完成: {Path(audio_path).name}")
        # 若启用删除源文件，删除原视频文件
        if cfg.delete_source_after_convert and os.path.exists(original_path):
            os.remove(original_path)
            cb(_Pct.CONVERT_SOURCE_DELETED, f"已删除源文件: {Path(original_path).name}")
        return audio_path
    except ProcessCancelledError:
        raise
    except Exception as e:
        raise RuntimeError(f"视频转音频失败: {e}") from e


def _step_search(
    title: str,
    artist: str,
    alternates: list[tuple[str, str]],
    cfg: ProcessingConfig,
    cb: Callable[[int, str], None],
) -> _SearchOutcome:
    """联网搜索官方歌词 + 专辑/封面信息（失败时用备选标题/艺术家重试）"""
    cb(_Pct.SEARCH, f"正在联网搜索歌词: {title} - {artist}")
    search_result = search_lyrics(title, artist, providers=cfg.providers)

    if not search_result:
        for alt_title, alt_artist in alternates:
            cb(_Pct.SEARCH, f"尝试备选: {alt_title} - {alt_artist}")
            search_result = search_lyrics(alt_title, alt_artist, providers=cfg.providers)
            if search_result:
                title, artist = alt_title, alt_artist
                break

    official_lrc = ""
    source = ""
    song_info: dict = {}
    if search_result:
        official_lrc, source, song_info = search_result
        song_info = song_info or {}

    # 若歌词搜索未返回专辑/封面，独立搜索一次
    if not song_info.get("album") and not song_info.get("cover_url") \
            and not song_info.get("matched_title"):
        cb(_Pct.SEARCH_INFO, "正在搜索专辑信息...")
        extra_info = search_song_info(title, artist, providers=cfg.providers)
        if extra_info:
            song_info.update({k: v for k, v in extra_info.items() if v})

    return _SearchOutcome(
        title=title, artist=artist,
        official_lrc=official_lrc, source=source, song_info=song_info,
    )


def _step_write_tags(
    audio_path: str, outcome: _SearchOutcome, cb: Callable[[int, str], None]
) -> None:
    """下载封面 + 写入音频标签（标题/艺术家/专辑/封面，已有字段保持不动）"""
    song_info = outcome.song_info

    cover_bytes = None
    cover_url = song_info.get("cover_url", "")
    if cover_url:
        cb(_Pct.COVER, "正在下载专辑封面...")
        cover_bytes = download_cover(cover_url)

    # 用联网匹配到的歌曲名/歌手名覆盖（比文件名解析更准确）
    tag_title = song_info.get("matched_title") or outcome.title
    tag_artist = song_info.get("matched_artist") or outcome.artist

    cb(_Pct.TAGS, "正在写入音频标签...")
    tag_result = write_tags(
        audio_path,
        title=tag_title,
        artist=tag_artist,
        album=song_info.get("album", ""),
        cover_bytes=cover_bytes,
    )
    written = [k for k, v in tag_result.items() if v]
    if written:
        cb(_Pct.TAGS_DONE, f"已写入标签: {', '.join(written)}")


def _step_save_official_lrc(
    outcome: _SearchOutcome,
    lrc_path: str,
    filename: str,
    cb: Callable[[int, str], None],
) -> str:
    """保存官方歌词（繁体转简体）"""
    official_lrc = zhconv.convert(outcome.official_lrc, "zh-cn")
    cb(_Pct.SAVE_OFFICIAL, f"找到官方歌词（来源: {outcome.source}），正在保存...")
    save_lrc(official_lrc, lrc_path)
    cb(_Pct.DONE, f"完成（官方歌词 · {outcome.source}）: {filename}")
    return f"完成（官方歌词 · {outcome.source}）→ {lrc_path}"


def _step_recognize(
    audio_path: str,
    outcome: _SearchOutcome,
    cfg: ProcessingConfig,
    lrc_path: str,
    filename: str,
    cb: Callable[[int, str], None],
    cancel_event: threading.Event | None,
) -> str:
    """未找到官方歌词 → Demucs 人声分离 + Whisper 语音识别 → 生成 LRC"""
    if not cfg.use_demucs and not cfg.use_whisper:
        msg = "未找到官方歌词，且未启用语音识别（Demucs/Whisper），跳过该文件"
        cb(_Pct.DONE, msg)
        return f"{msg}: {filename}"

    cb(_Pct.PREPARE_ASR, "未找到官方歌词，准备语音识别...")

    # 人声分离（仅在启用时执行）
    vocals_path = audio_path
    if cfg.use_demucs:
        cb(_Pct.SEPARATE, f"正在使用 Demucs ({cfg.demucs_model}) 分离人声...")
        vocals_path = separate_vocals(
            audio_path, model_name=cfg.demucs_model, cancel_event=cancel_event
        )
        cb(_Pct.SEPARATE_DONE, "人声分离完成")
    else:
        cb(_Pct.SEPARATE, "未启用 Demucs，使用原始音频进行识别...")

    # Whisper 识别
    if not cfg.use_whisper:
        msg = "未启用 Whisper，无法进行语音识别，跳过该文件"
        cb(_Pct.DONE, msg)
        return f"{msg}: {filename}"

    cb(_Pct.TRANSCRIBE, f"正在使用 Whisper ({cfg.whisper_model}) 识别歌词...")
    segments = transcribe(vocals_path, model_name=cfg.whisper_model)

    if not segments:
        cb(_Pct.DONE, f"未识别到任何歌词: {filename}")
        return f"未识别到歌词: {filename}"

    # 繁体转简体
    for seg in segments:
        seg["text"] = zhconv.convert(seg["text"], "zh-cn")

    # 生成 LRC 并保存
    cb(_Pct.BUILD_LRC, "正在生成 LRC 文件...")
    lrc_content = build_lrc_from_whisper(
        segments, title=outcome.title, artist=outcome.artist
    )
    save_lrc(lrc_content, lrc_path)
    cb(_Pct.LRC_SAVED, f"LRC 已保存: {lrc_path}")

    return f"完成（Whisper 识别 · {cfg.whisper_model}）→ {lrc_path}"
