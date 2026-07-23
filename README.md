# 🎵 AudioToLyrics v4

从音视频文件中自动识别歌词，生成 LRC 歌词文件的桌面应用。同时支持联网搜索歌曲信息、写入音频文件tag。

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## ✨ 功能特性

- 🎬 **视频自动转音频** — 检测到视频文件自动无损提取音轨为 FLAC
- 🔍 **联网搜索歌词** — 优先从 QQ音乐、酷狗、LRCLib、网易云搜索官方歌词
- 🎼 **专辑封面下载** — 自动搜索专辑信息并下载封面写入音频文件
- 📝 **音频 tag 写入** — 自动写入标题/艺术家/专辑/封面（已有则保持不动）
- 🎤 **Demucs 人声分离** — 用户可选启用，提取纯净人声
- 🎙️ **faster-whisper 识别** — 用户可选启用，支持多语言，自动检测语言
- 🔄 **繁简转换** — 繁体中文自动转简体
- 📐 **相似度校验** — 防止歌词误匹配（标题+歌手双重校验）
- 🖥️ **GPU 加速** — Demucs 和 Whisper 均支持 CUDA 加速
- 🗂️ **批量处理** — 支持拖拽添加多个音视频文件
- 💾 **智能识别** — 无音频tag时，支持识别 "歌名"、"歌名-歌手"、"歌手-歌名" 文件名格式

## 📋 系统要求

- Python 3.10+
- Windows / Linux / macOS
- **联网环境**（歌词搜索、专辑封面下载、歌曲信息匹配均需联网）
- （推荐）NVIDIA GPU + CUDA 用于加速

## 🚀 安装与运行

```bash
# 进入项目目录
cd audio_to_lrc-v2

# 安装依赖
pip install -r requirements.txt

# 启动程序
python main.py
```

> **GPU 加速**：如需使用 CUDA，请安装 GPU 版 PyTorch：
> ```bash
> pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
> ```

## 📖 使用方法

1. **添加文件** — 拖拽音视频文件到左侧面板，或点击「添加文件」按钮
2. **调整设置** — 右侧可设置功能开关、Whisper/Demucs 模型、选择歌词搜索平台
3. **开始处理** — 点击「开始」按钮，等待处理完成
4. **输出结果** — LRC 文件自动保存在音视频文件同目录下

> **提示**：优先读取音频tag获取歌曲信息。若无tag，音视频文件建议命名为 `歌名.mp3`、`歌名-歌手.mp3` 或 `歌手-歌名.mp3`，以提高联网搜索匹配成功率。

## 🏗️ 项目结构

```
audio_to_lrc-v2/
├── main.py                 # 程序入口
├── config.py               # 全局配置
├── requirements.txt        # 依赖列表
├── core/                   # 核心处理逻辑
│   ├── pipeline.py         #   处理流水线编排
│   ├── internet_search.py  #   联网搜索（歌词/专辑/封面/歌曲名/歌手名）
│   ├── video_converter.py  #   视频无损转音频（FFmpeg）
│   ├── tag_writer.py       #   音频 tag 写入（mutagen）
│   ├── separator.py        #   Demucs 人声分离
│   ├── transcriber.py      #   faster-whisper 语音识别
│   └── lrc_builder.py      #   LRC 文件构建与对齐
├── gui/                    # CustomTkinter 界面
│   ├── app.py              #   主窗口
│   ├── file_panel.py       #   文件管理面板
│   ├── settings_panel.py   #   设置面板
│   ├── progress_panel.py   #   进度与日志面板
│   └── styles.py           #   样式常量
└── utils/                  # 工具函数
    ├── audio_info.py       #   音频元数据读取 + 文件名解析
    └── thread_worker.py    #   后台线程工作器
```

## ⚙️ 配置说明

编辑 `config.py` 可自定义：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `WHISPER_MODELS` | 可选 Whisper 模型 | tiny ~ large |
| `DEFAULT_WHISPER_MODEL` | 默认模型 | large |
| `DEMUCS_MODELS` | 可选 Demucs 模型 | htdemucs / htdemucs_ft |
| `LYRICS_PROVIDERS` | 歌词搜索平台优先级 | QQMusic > Kugou > lrclib > NetEase |
| `VIDEO_FORMATS` | 支持的视频格式 | mp4/mkv/avi/mov/webm/flv |
| `SUPPORTED_MEDIA_FORMATS` | 所有支持的格式 | 音频 + 视频 |

## 📝 依赖说明

| 依赖 | 用途 |
|------|------|
| [customtkinter](https://github.com/TomSchimansky/CustomTkinter) | 现代化 GUI 界面 |
| [demucs](https://github.com/facebookresearch/demucs) | 人声分离（可选启用） |
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | 高效 Whisper 语音识别（可选启用） |
| [syncedlyrics](https://github.com/rtcqz/syncedlyrics) | 联网歌词搜索 |
| [mutagen](https://github.com/quodlibet/mutagen) | 音频元数据读取 + tag 写入 |
| [imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg) | FFmpeg 二进制自动下载（视频转音频） |
| [zhconv](https://github.com/gumblex/zhconv) | 繁简中文转换 |

## 📄 许可证

MIT License

## 🙏 致谢

- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — 高效的 Whisper 实现
- [Demucs](https://github.com/facebookresearch/demucs) — Meta 的音源分离工具
- [syncedlyrics](https://github.com/rtcqz/syncedlyrics) — 多平台歌词搜索库
