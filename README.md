# 🎵 AudioToLyrics v5

从音视频文件中自动识别歌词，生成 LRC 歌词文件的桌面应用。同时支持联网搜索歌曲信息、写入音频文件tag、歌手头像获取。

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## ✨ 功能特性

- 🔓 **加密音频解密** — 自动解密网易云(.ncm)、QQ音乐(.qmc/.mflac/.mgg)、酷狗(.kgm)、酷我(.kwm)、虾米(.xm)等加密格式，首次使用自动下载解密工具
- 🎬 **视频自动转音频** — 检测到视频文件自动无损提取音轨为 FLAC
- 🔍 **联网搜索歌词** — 优先从 QQ音乐、酷狗、LRCLib、网易云搜索官方歌词
- 🎼 **专辑封面下载** — 自动搜索专辑信息并下载封面写入音频文件
- 📝 **音频 tag 写入** — 自动写入标题/艺术家/专辑/封面（已有则保持不动）
- 🎤 **Demucs 人声分离** — 用户可选启用，首次启用时自动下载安装
- 🎙️ **faster-whisper 识别** — 用户可选启用，首次启用时自动下载安装
- 🖼️ **歌手头像获取** — 扫描音乐库提取歌手信息，联网搜索并下载歌手头像
- 🌗 **亮/暗主题切换** — 支持暗色和亮色两套界面主题，重启后生效
- 📂 **通用输出目录** — 可设置输出目录，处理成功的文件自动移动到该目录
- 🔄 **繁简转换** — 繁体中文自动转简体
- 📐 **相似度校验** — 防止歌词误匹配（标题+歌手双重校验）
- 🖥️ **GPU 加速** — Demucs 和 Whisper 均支持 CUDA 加速
- 🗂️ **批量处理** — 支持拖拽添加多个音视频文件
- 🗑️ **转换后清理** — 可选转换后自动删除源文件（加密/视频），默认保留
- 💾 **智能识别** — 无音频tag时，支持识别 "歌名"、"歌名-歌手"、"歌手-歌名" 文件名格式
- 📦 **依赖按需安装** — demucs/faster-whisper/imageio-ffmpeg 不再强制预装，启用对应功能时自动 pip install

## 📋 系统要求

- Python 3.10+
- Windows / Linux / macOS
- **联网环境**（歌词搜索、专辑封面下载、歌曲信息匹配、歌手头像获取均需联网）
- （推荐）NVIDIA GPU + CUDA 用于加速

## 🚀 安装与运行

```bash
# 进入项目目录
git clone <repo-url>
cd AudioToLyrics

# 安装核心依赖
pip install -r requirements.txt

# 启动程序
python main.py
```

> **按需依赖**：demucs、faster-whisper、imageio-ffmpeg 无需手动安装，启用对应功能时程序会自动下载安装。
>
> **GPU 加速**：如需使用 CUDA，请安装 GPU 版 PyTorch：
> ```bash
> pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
> ```

## 📖 使用方法

1. **添加文件** — 拖拽音视频文件到左侧面板，或点击「添加文件」按钮（支持加密音频、普通音视频文件）
2. **调整设置** — 右侧设置面板可配置功能开关、输出目录、Whisper/Demucs 模型、歌词搜索平台、界面主题
3. **开始处理** — 点击「开始」按钮，等待处理完成
4. **输出结果** — LRC 文件自动保存在源文件同目录（若设置了输出目录则移动到输出目录）

> **提示**：优先读取音频tag获取歌曲信息。若无tag，音视频文件建议命名为 `歌名.mp3`、`歌名-歌手.mp3` 或 `歌手-歌名.mp3`，以提高联网搜索匹配成功率。

### 歌手头像获取

1. 在右侧设置面板点击「联网搜索获取歌手头像」按钮
2. 选择音乐库所在文件夹
3. 程序自动扫描音频 tag 中的歌手信息，联网搜索头像并保存到 `{音乐库}/ArtistImage/` 目录

## 🏗️ 项目结构

```
AudioToLyrics/
├── main.py                 # 程序入口
├── config.py               # 全局配置
├── requirements.txt        # 核心依赖列表
├── user_settings.json      # 用户偏好（主题等，运行时自动创建）
├── tools/                  # 外部工具目录
│   └── um.exe              #   unlock-music CLI（首次使用时自动下载）
├── core/                   # 核心处理逻辑
│   ├── pipeline.py         #   处理流水线编排
│   ├── decryptor.py        #   加密音频解密（unlock-music）
│   ├── internet_search.py  #   联网搜索（歌词/专辑/封面/歌曲名/歌手名/歌手头像）
│   ├── artist_image.py     #   歌手头像扫描与下载
│   ├── video_converter.py  #   视频无损转音频（FFmpeg）
│   ├── tag_writer.py       #   音频 tag 写入（mutagen）
│   ├── separator.py        #   Demucs 人声分离
│   ├── transcriber.py      #   faster-whisper 语音识别
│   └── lrc_builder.py      #   LRC 文件构建与对齐
├── gui/                    # CustomTkinter 界面
│   ├── app.py              #   主窗口（左右分栏布局）
│   ├── file_panel.py       #   文件管理面板
│   ├── settings_panel.py   #   设置面板
│   ├── progress_panel.py   #   进度与日志面板
│   └── styles.py           #   样式常量 + 主题系统
└── utils/                  # 工具函数
    ├── audio_info.py       #   音频元数据读取 + 文件名解析
    ├── dep_installer.py    #   依赖按需安装器
    └── thread_worker.py    #   后台线程工作器
```

## ⚙️ 配置说明

编辑 `config.py` 可自定义：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `WHISPER_MODELS` | 可选 Whisper 模型 | tiny ~ large |
| `DEFAULT_WHISPER_MODEL` | 默认模型 | large |
| `DEMUCS_MODELS` | 可选 Demucs 模型 | htdemucs / htdemucs_ft |
| `LYRICS_PROVIDERS` | 歌曲信息搜索平台优先级 | QQMusic > Kugou > NetEase > lrclib |
| `ENCRYPTED_FORMATS` | 支持的加密音频格式 | ncm/qmc/mflac/mgg/kgm/kwm/xm 等 |
| `VIDEO_FORMATS` | 支持的视频格式 | mp4/mkv/avi/mov/webm/flv |
| `SUPPORTED_MEDIA_FORMATS` | 所有支持的格式 | 音频 + 视频 + 加密音频 |

## 📝 依赖说明

### 核心依赖（requirements.txt）

| 依赖 | 用途 |
|------|------|
| [customtkinter](https://github.com/TomSchimansky/CustomTkinter) | 现代化 GUI 界面 |
| [syncedlyrics](https://github.com/rtcqz/syncedlyrics) | 联网歌词搜索 |
| [mutagen](https://github.com/quodlibet/mutagen) | 音频元数据读取 + tag 写入 |
| [requests](https://github.com/psf/requests) | HTTP 请求（搜索/下载） |
| [zhconv](https://github.com/gumblex/zhconv) | 繁简中文转换 |

### 按需依赖（启用对应功能时自动安装）

| 依赖 | 用途 | 触发条件 |
|------|------|----------|
| [demucs](https://github.com/facebookresearch/demucs) | 人声分离 | 勾选「Demucs 人声分离」 |
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | 高效 Whisper 语音识别 | 勾选「Whisper 识别」 |
| [imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg) | FFmpeg 二进制（视频转音频） | 处理视频文件时 |

## 🔓 加密音频支持

程序集成了 [unlock-music CLI](https://git.unlock-music.dev/um/cli) 用于解密各音乐平台的加密音频格式：

| 平台 | 支持的加密格式 |
|------|----------------|
| 网易云音乐 | .ncm |
| QQ音乐 | .qmc0/.qmc2/.qmc3/.qmcflac/.qmcogg/.tkm/.mflac/.mgg |
| 酷狗音乐 | .kgm/.vpr |
| 酷我音乐 | .kwm |
| 虾米音乐 | .xm |

首次处理加密文件时，程序会自动下载解密工具到 `tools/` 目录，无需手动安装。

## 🌗 主题切换

- 在设置面板底部「界面主题」区块选择暗色/亮色
- 选择后自动保存，重启程序后生效
- 用户偏好存储在 `user_settings.json`

## 📄 许可证

MIT License

## 🙏 致谢

- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — 高效的 Whisper 实现
- [Demucs](https://github.com/facebookresearch/demucs) — Meta 的音源分离工具
- [syncedlyrics](https://github.com/rtcqz/syncedlyrics) — 多平台歌词搜索库
- [unlock-music](https://git.unlock-music.dev/um/cli) — 音乐平台加密音频解密工具
