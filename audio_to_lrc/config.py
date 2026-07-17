"""
全局配置常量
"""

import os

# ── 应用信息 ──────────────────────────────────────────────
APP_TITLE = "🎵 歌曲歌词识别器"
APP_VERSION = "2.0"
APP_SUBTITLE = "从歌曲中自动识别歌词，生成 LRC 文件"

# ── 窗口 ──────────────────────────────────────────────────
WINDOW_WIDTH = 700
WINDOW_HEIGHT = 600

# ── Whisper ───────────────────────────────────────────────
AVAILABLE_MODELS = ["tiny", "base", "small", "medium", "large-v3"]
DEFAULT_MODEL = "small"

# 模型缓存目录（faster-whisper 默认 ~/.cache/huggingface）
MODEL_CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "audio_to_lrc_models")

# ── 音频 ──────────────────────────────────────────────────
SUPPORTED_AUDIO_FORMATS = [
    ("音频文件", "*.mp3 *.wav *.m4a *.flac *.ogg *.wma *.aac"),
    ("所有文件", "*.*"),
]
TARGET_SAMPLE_RATE = 16000  # Whisper 期望的采样率

# ── 语言 ──────────────────────────────────────────────────
LANGUAGE_OPTIONS = {
    "zh (中文)": "zh",
    "en (英语)": "en",
    "ja (日语)": "ja",
    "ko (韩语)": "ko",
    "auto (自动检测)": None,
}
DEFAULT_LANGUAGE = "zh (中文)"

# ── Demucs ────────────────────────────────────────────────
DEMUCS_TIMEOUT = 600  # 秒
DEMUCS_MODEL = "htdemucs"

# ── LRC ───────────────────────────────────────────────────
LRC_MIN_TEXT_LENGTH = 2  # 最短有效歌词字符数

# ── 设备 ──────────────────────────────────────────────────
# compute_type 映射：GPU 用 float16 更快，CPU 用 int8 省内存
DEVICE_COMPUTE_MAP = {
    "cuda": "float16",
    "cpu": "int8",
}