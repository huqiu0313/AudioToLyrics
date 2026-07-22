"""LRC 格式化输出：将 Whisper 识别结果或官方歌词转换为标准 LRC 文件"""

import os
from pathlib import Path


def build_lrc_from_whisper(
    segments: list[dict],
    title: str = "",
    artist: str = "",
) -> str:
    """
    将 Whisper 段落时间戳转换为标准 LRC 格式。

    参数:
        segments: [{start: float, end: float, text: str}, ...]
        title: 歌曲标题（写入元数据头）
        artist: 艺术家（写入元数据头）

    返回:
        LRC 格式的字符串
    """
    lines = []

    # LRC 元数据头
    if title:
        lines.append(f"[ti:{title}]")
    if artist:
        lines.append(f"[ar:{artist}]")
    lines.append("[by:AudioToLyrics]")
    lines.append("")

    # 歌词行（带时间戳）
    for seg in segments:
        ts = _format_timestamp(seg["start"])
        text = seg["text"].strip()
        if text:
            lines.append(f"{ts}{text}")

    return "\n".join(lines)


def save_lrc(content: str, output_path: str) -> None:
    """
    将 LRC 内容写入文件（UTF-8 编码）。

    参数:
        content: LRC 格式字符串
        output_path: 输出文件路径（.lrc）
    """
    os.makedirs(Path(output_path).parent, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)


def get_lrc_path(audio_path: str, output_dir: str | None = None) -> str:
    """
    根据音频路径生成对应的 LRC 输出路径。

    参数:
        audio_path: 音频文件路径
        output_dir: 输出目录，None 则与音频同目录

    返回:
        LRC 文件路径字符串
    """
    audio_path = Path(audio_path)
    if output_dir:
        return str(Path(output_dir) / (audio_path.stem + ".lrc"))
    return str(audio_path.with_suffix(".lrc"))


def _format_timestamp(seconds: float) -> str:
    """将秒数转换为 LRC 时间戳格式 [mm:ss.xx]"""
    if seconds < 0:
        seconds = 0
    minutes = int(seconds // 60)
    secs = seconds - minutes * 60
    return f"[{minutes:02d}:{secs:05.2f}]"
