"""可选依赖探测：AI 组件（demucs/faster-whisper）在安装版中不打包"""

import importlib.util


def has_demucs() -> bool:
    """demucs 人声分离是否可用"""
    return importlib.util.find_spec("demucs") is not None


def has_whisper() -> bool:
    """faster-whisper 语音识别是否可用"""
    return importlib.util.find_spec("faster_whisper") is not None
