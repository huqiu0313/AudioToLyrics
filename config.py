"""全局配置常量"""

# 版本号（窗口标题、docstring 等统一引用此处）
VERSION = "4.0"

# 网络请求超时（秒）
HTTP_TIMEOUT = 8                # 歌词/专辑信息搜索
COVER_DOWNLOAD_TIMEOUT = 10     # 封面下载
COVER_MIN_BYTES = 500           # 小于该字节数的封面响应视为无效
UM_DOWNLOAD_TIMEOUT = 120       # unlock-music CLI 下载

# 子进程超时（秒）
SUBPROCESS_TIMEOUT = 600        # demucs 人声分离 / ffmpeg 视频转音频
UM_RUN_TIMEOUT = 120            # unlock-music 解密

# 支持的音频文件格式
SUPPORTED_FORMATS = (".mp3", ".wav", ".flac", ".m4a", ".ogg", ".aac", ".wma")

# 支持的视频文件格式
VIDEO_FORMATS = (".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv")

# 支持的加密音频文件格式（需通过 unlock-music 解密）
ENCRYPTED_FORMATS = (
    # 网易云音乐
    ".ncm",
    # QQ音乐
    ".qmc0", ".qmc2", ".qmc3", ".qmcflac", ".qmcogg", ".tkm", ".mflac", ".mgg",
    # 酷狗音乐
    ".kgm", ".vpr",
    # 酷我音乐
    ".kwm",
    # 虾米音乐
    ".xm",
)

# 所有支持的媒体格式（音频 + 视频 + 加密音频）
SUPPORTED_MEDIA_FORMATS = SUPPORTED_FORMATS + VIDEO_FORMATS + ENCRYPTED_FORMATS

# unlock-music CLI 二进制文件名
UM_CLI_NAME = "um.exe"

# unlock-music CLI 自动下载地址（Gitee 镜像）
UM_CLI_DOWNLOAD_URL = "https://gitee.com/pnceon/unlock-music/releases/download/v0.1/unlock-music.zip"
# zip 包内 Windows amd64 可执行文件的相对路径
UM_CLI_ZIP_ENTRY = "unlock-music/exe/um-windows-amd64.exe"

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
WINDOW_TITLE = f"AudioToLyrics v{VERSION}"
WINDOW_WIDTH = 920
WINDOW_HEIGHT = 640
WINDOW_MIN_WIDTH = 800
WINDOW_MIN_HEIGHT = 600
