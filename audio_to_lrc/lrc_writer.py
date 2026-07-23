"""
LRC 歌词文件写入模块
"""

import os
import logging

from utils import format_lrc_time
from lyric_breaks import split_lyrics_by_rhythm

logger = logging.getLogger(__name__)


def save_lrc(lyrics: list[tuple[float, float, str]],
             audio_path: str,
             log_callback=None) -> str:
    """
    将识别结果保存为 LRC 文件。

    Args:
        lyrics: [(start, end, text), ...] 格式的歌词列表
        audio_path: 原始音频文件路径（用于生成同名 .lrc 文件）
        log_callback: 日志回调函数

    Returns:
        生成的 LRC 文件路径
    """
    def _log(msg: str):
        if log_callback:
            log_callback(msg)
        logger.info(msg)

    base = os.path.splitext(audio_path)[0]
    lrc_path = f"{base}.lrc"

    try:
        broken_lyrics = split_lyrics_by_rhythm(lyrics)
        with open(lrc_path, 'w', encoding='utf-8') as f:
            # 写入 LRC 头部元信息
            f.write("[ti:]\n[ar:]\n[al:]\n[by:AudioToLRC GUI]\n[offset:0]\n\n")

            # 写入歌词行
            for start, end, text in broken_lyrics:
                time_tag = format_lrc_time(start)
                f.write(f"{time_tag}{text}\n")

        _log(f"💾 歌词已保存: {lrc_path}")

        # 预览前几行
        _log("\n--- 预览 ---")
        for start, end, text in broken_lyrics[:8]:
            time_tag = format_lrc_time(start)
            _log(f"{time_tag} {text}")

        return lrc_path

    except PermissionError:
        _log(f"❌ 无法写入文件（权限不足）: {lrc_path}")
        raise
    except OSError as e:
        _log(f"❌ 写入 LRC 文件失败: {e}")
        raise


def save_empty_lrc(audio_path: str, log_callback=None) -> str:
    """
    生成空的 LRC 文件（未识别到歌词时使用）。

    Args:
        audio_path: 原始音频文件路径
        log_callback: 日志回调函数

    Returns:
        生成的 LRC 文件路径
    """
    def _log(msg: str):
        if log_callback:
            log_callback(msg)
        logger.info(msg)

    base = os.path.splitext(audio_path)[0]
    lrc_path = f"{base}.lrc"

    try:
        with open(lrc_path, 'w', encoding='utf-8') as f:
            f.write("[ti:]\n[ar:]\n[al:]\n[by:AudioToLRC GUI]\n[offset:0]\n\n")

        _log(f"💾 空歌词文件: {lrc_path}")
        return lrc_path

    except PermissionError:
        _log(f"❌ 无法写入文件（权限不足）: {lrc_path}")
        raise
    except OSError as e:
        _log(f"❌ 写入 LRC 文件失败: {e}")
        raise
