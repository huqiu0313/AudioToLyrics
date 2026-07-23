"# 🎵 歌曲歌词识别器 (Audio to LRC)

从歌曲中自动识别歌词，生成 LRC 歌词文件的桌面应用。

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## ✨ 功能特性

- 🎤 **人声分离** - 使用 Demucs 提取人声，大幅提高识别准确率
- 🎙️ **语音识别** - 基于 faster-whisper，支持多语言（中/英/日/韩）
- 📝 **LRC 生成** - 自动生成带时间轴的歌词文件
- 🌐 **官方歌词检索** - 优先联网搜索歌曲官方歌词文本，并按顺序与 Whisper 时间片段对齐
- 🔄 **简繁转换** - 自动将繁体中文转换为简体
- 🖥️ **GPU 加速** - 自动检测 CUDA，支持 GPU 加速推理
- 💾 **模型缓存** - Whisper 模型只加载一次，后续复用

## 📋 系统要求

- Python 3.10+
- Windows / Linux / macOS
- （可选）NVIDIA GPU + CUDA 用于加速

## 🚀 安装

### 1. 克隆仓库

```bash
git clone https://github.com/your-username/audio-to-lrc.git
cd audio-to-lrc
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 运行程序

```bash
python main.py
```

## 📖 使用方法

1. 点击「浏览」选择音频文件（支持 mp3/wav/m4a/flac 等格式）
2. 选择识别模型（推荐 `small`，平衡速度和准确率）
3. 选择歌词语言
4. 保留「联网搜索官方歌词文本并对齐时间戳」勾选项（推荐）
5. 点击「开始识别」
6. 等待处理完成，LRC 文件会自动保存到音频文件同目录

## 🏗️ 项目结构

```
audio_to_lrc/
│
├── main.py              # 程序入口
├── gui.py               # Tkinter 图形界面
├── recognizer.py        # Whisper 语音识别
├── separator.py         # Demucs 人声分离
├── lrc_writer.py        # LRC 歌词文件写入
├── config.py            # 全局配置常量
├── utils.py             # 工具函数
└── __init__.py          # 包初始化
```

## ⚙️ 配置说明

编辑 `config.py` 可以修改：

- `DEFAULT_MODEL` - 默认 Whisper 模型（tiny/base/small/medium/large-v3）
- `TARGET_SAMPLE_RATE` - 目标采样率（默认 16000）
- `DEMUCS_TIMEOUT` - Demucs 超时时间（默认 600 秒）

## 🐛 常见问题

### 1. 识别速度慢

- 使用更小的模型（如 `tiny` 或 `base`）
- 确保已安装 CUDA 和 GPU 版本的 PyTorch

### 2. 人声分离失败

- 检查 Demucs 是否正确安装：`pip install demucs`
- 首次运行需要下载模型（约 800MB）

### 3. 内存不足

- 使用更小的模型
- 关闭其他占用内存的程序

## 📝 依赖说明

- **faster-whisper** - Whisper 语音识别
- **demucs** - 人声分离
- **librosa** - 音频处理
- **soundfile** - 音频读写
- **torch** - PyTorch（GPU 加速）
- **zhconv** - 简繁转换
- **tkinter** - GUI（Python 内置）

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 🙏 致谢

- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) - 高效的 Whisper 实现
- [Demucs](https://github.com/facebookresearch/demucs) - Facebook 的人声分离工具
- [OpenAI Whisper](https://github.com/openai/whisper) - 语音识别模型

---

**注意**：本项目仅供学习研究使用，请勿用于商业用途。请尊重版权，合法使用。
"