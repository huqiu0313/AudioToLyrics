"""视频转音频：检测视频格式并无损提取音轨为 FLAC"""

import threading
from pathlib import Path

from config import SUBPROCESS_TIMEOUT, VIDEO_FORMATS
from utils.process import run_cancellable


def is_video(file_path: str) -> bool:
    """判断文件是否为视频格式"""
    return Path(file_path).suffix.lower() in VIDEO_FORMATS


def convert_to_audio(
    video_path: str,
    output_dir: str | None = None,
    cancel_event: threading.Event | None = None,
) -> str:
    """
    将视频文件无损提取音轨为 FLAC 格式。

    使用 imageio-ffmpeg 自动下载的 FFmpeg 二进制文件，无需用户手动安装。
    输出文件与视频同名，后缀改为 .flac，存放在源文件同目录（或指定目录）。

    参数:
        video_path: 视频文件路径
        output_dir: 输出目录，None 则与视频同目录
        cancel_event: 可选的取消事件，set 后 ffmpeg 子进程会被终止

    返回:
        生成的音频文件路径
    """
    import imageio_ffmpeg  # 延迟导入：首次使用时才触发 ffmpeg 二进制定位

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

    result = run_cancellable(cmd, timeout=SUBPROCESS_TIMEOUT, cancel_event=cancel_event)
    if result.returncode != 0:
        raise RuntimeError(f"视频转音频失败: {result.stderr[:300]}")

    if not out_path.exists():
        raise FileNotFoundError(f"转换后文件不存在: {out_path}")

    return str(out_path)
