"""视频转音频：检测视频格式并无损提取音轨为 FLAC"""

import subprocess
from pathlib import Path

from config import VIDEO_FORMATS


def is_video(file_path: str) -> bool:
    """判断文件是否为视频格式"""
    return Path(file_path).suffix.lower() in VIDEO_FORMATS


def convert_to_audio(video_path: str, output_dir: str | None = None) -> str:
    """
    将视频文件无损提取音轨为 FLAC 格式。

    使用 imageio-ffmpeg 自动下载的 FFmpeg 二进制文件，无需用户手动安装。
    输出文件与视频同名，后缀改为 .flac，存放在源文件同目录（或指定目录）。

    参数:
        video_path: 视频文件路径
        output_dir: 输出目录，None 则与视频同目录

    返回:
        生成的音频文件路径
    """
    import imageio_ffmpeg

    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
    video_path = Path(video_path)

    if output_dir:
        out_path = Path(output_dir) / (video_path.stem + ".flac")
        out_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        out_path = video_path.with_suffix(".flac")

    # 如果已存在，直接返回
    if out_path.exists():
        return str(out_path)

    cmd = [
        ffmpeg_path,
        "-i", str(video_path),
        "-vn",                # 不要视频
        "-acodec", "flac",    # 无损 FLAC 编码
        "-y",                 # 覆盖输出
        str(out_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"视频转音频失败: {result.stderr[:300]}")

    if not out_path.exists():
        raise FileNotFoundError(f"转换后文件不存在: {out_path}")

    return str(out_path)
