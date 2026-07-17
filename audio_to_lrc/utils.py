"""
工具函数：设备检测、文本清洗、时间格式化
"""

import re


def detect_device() -> tuple[str, str]:
    """
    自动检测最佳计算设备。
    优先 CUDA (GPU)，否则回退到 CPU。
    """
    try:
        import torch
        if torch.cuda.is_available():
            device_name = torch.cuda.get_device_name(0)
            return "cuda", device_name
    except ImportError:
        pass
    return "cpu", "CPU"


def clean_lyric_text(text: str) -> str:
    """
    清洗单条歌词文本：
    - 移除音乐符号 emoji
    - 移除书名号等无关标点
    - 合并连续空白
    """
    text = re.sub(r'[♪♫♬♩🎵🎶🎤🎧]', '', text)
    text = re.sub(r'[【】〈〉《》「」『』]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def format_lrc_time(seconds: float) -> str:
    """
    将秒数转换为 LRC 时间标签格式 [mm:ss.xx]
    例如: 65.32 -> [01:05.32]
    """
    mins = int(seconds // 60)
    secs = seconds % 60
    return f"[{mins:02d}:{secs:05.2f}]"
