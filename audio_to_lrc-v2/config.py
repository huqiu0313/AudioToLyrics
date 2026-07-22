"""全局配置常量"""

# 支持的音频文件格式
SUPPORTED_FORMATS = (".mp3", ".wav", ".flac", ".m4a", ".ogg", ".aac", ".wma")

# 支持的视频文件格式
VIDEO_FORMATS = (".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv")

# 所有支持的媒体格式（音频 + 视频）
SUPPORTED_MEDIA_FORMATS = SUPPORTED_FORMATS + VIDEO_FORMATS

# Whisper 可选模型（tiny 最快但准确率最低，large 最慢但最准）
WHISPER_MODELS = ("tiny", "base", "small", "medium", "large")
DEFAULT_WHISPER_MODEL = "large"

# Demucs 可选模型
DEMUCS_MODELS = ("htdemucs", "htdemucs_ft")
DEFAULT_DEMUCS_MODEL = "htdemucs"

# 歌词搜索平台（按优先级排序）
LYRICS_PROVIDERS = ["QQMusic", "Kugou",  "NetEase", "lrclib"]
LYRICS_PROVIDER_LABELS = {
    "lrclib": "LRCLib",
    "NetEase": "网易云音乐",
    "QQMusic": "QQ音乐",
    "Kugou": "酷狗音乐",
}

# GUI 设置
WINDOW_TITLE = "AudioToLyrics v4"
WINDOW_WIDTH = 920
WINDOW_HEIGHT = 600
WINDOW_MIN_WIDTH = 800
WINDOW_MIN_HEIGHT = 550
