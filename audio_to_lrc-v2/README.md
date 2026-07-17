# 🎵 AudioToLyrics v2

从音频文件中自动识别歌词，生成 LRC 歌词文件的桌面应用。

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## ✨ 功能特性

- 🔍 **联网搜索歌词** — 优先从 QQ音乐、酷狗、LRCLib、网易云搜索官方歌词
- 🎤 **Demucs 人声分离** — 子进程运行，提取纯净人声
- 🎙️ **faster-whisper 识别** — 支持多语言（中/英/日/韩），自动检测语言
- 🔄 **繁简转换** — 繁体中文自动转简体
- 📐 **相似度校验** — 防止歌词误匹配（标题+歌手双重校验）
- 🖥️ **GPU 加速** — Demucs 和 Whisper 均支持 CUDA 加速
- 🗂️ **批量处理** — 支持拖拽添加多个音频文件
- 💾 **智能命名** — 支持 "歌名"、"歌名-歌手"、"歌手-歌名" 文件名格式

## 📋 系统要求

- Python 3.10+
- Windows / Linux / macOS
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

1. **添加文件** — 拖拽音频文件到左侧面板，或点击「添加文件」按钮
2. **调整设置** — 右侧可设置 Whisper/Demucs 模型、选择歌词搜索平台
3. **开始处理** — 点击「开始」按钮，等待处理完成
4. **输出结果** — LRC 文件自动保存在音频文件同目录下

> **提示**：音频文件建议命名为 `歌名.mp3`、`歌名-歌手.mp3` 或 `歌手-歌名.mp3`，以提高联网搜索匹配成功率。

## 🏗️ 项目结构

```
audio_to_lrc-v2/
├── main.py                 # 程序入口
├── config.py               # 全局配置
├── requirements.txt        # 依赖列表
├── core/                   # 核心处理逻辑
│   ├── pipeline.py         #   处理流水线编排
│   ├── lyrics_search.py    #   联网歌词搜索 + 相似度校验
│   ├── separator.py        #   Demucs 人声分离（子进程）
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

## 📝 依赖说明

| 依赖 | 用途 |
|------|------|
| [customtkinter](https://github.com/TomSchimansky/CustomTkinter) | 现代化 GUI 界面 |
| [demucs](https://github.com/facebookresearch/demucs) | 人声分离（子进程调用） |
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | 高效 Whisper 语音识别 |
| [syncedlyrics](https://github.com/rtcqz/syncedlyrics) | 联网歌词搜索 |
| [mutagen](https://github.com/quodlibet/mutagen) | 音频元数据读取 |
| [zhconv](https://github.com/gumblex/zhconv) | 繁简中文转换 |

## 📄 许可证

MIT License

## 🙏 致谢

- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — 高效的 Whisper 实现
- [Demucs](https://github.com/facebookresearch/demucs) — Meta 的音源分离工具
- [syncedlyrics](https://github.com/rtcqz/syncedlyrics) — 多平台歌词搜索库
