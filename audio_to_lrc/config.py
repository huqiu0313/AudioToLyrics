"""
全局配置常量
"""

import os

# ── 应用信息 ──────────────────────────────────────────────
APP_TITLE = "🎵 歌曲歌词识别器"
APP_VERSION = "3.0"
APP_SUBTITLE = "联网搜索获取歌词，对齐时间戳，生成 LRC 文件"

# ── 窗口 ──────────────────────────────────────────────────
WINDOW_WIDTH = 700
WINDOW_HEIGHT = 600

# ── Whisper ───────────────────────────────────────────────
AVAILABLE_MODELS = [ "base", "small", "medium", "large-v3"]
DEFAULT_MODEL = "large-v3"

WHISPER_PROMPTS = {
    "zh": "请识别为中文歌词，保留自然断句和重复副歌，忽略背景音乐和噪音。",
    "en": "Transcribe as English song lyrics, preserve natural phrasing and repeated chorus, ignore background music and noise.",
    "ja": "日本語の歌詞として認識してください。自然な区切りと反復するサビを保ち、背景音楽とノイズを無視してください。",
    "ko": "한국어 가사로 인식해 주세요. 자연스러운 문장 분절과 반복되는 후렴을 유지하고 배경 음악과 노이즈는 무시하세요.",
}
DEFAULT_WHISPER_PROMPT = "请识别为歌词，保留自然断句和重复副歌，忽略背景音乐和噪音。"

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