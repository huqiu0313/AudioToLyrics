"""
audio_to_lrc - 歌曲歌词识别器 v2.0
从歌曲中自动识别歌词，生成 LRC 文件

模块结构:
  config.py       - 全局配置常量
  utils.py        - 工具函数（设备检测、文本清洗、时间格式化）
  separator.py    - Demucs 人声分离
  recognizer.py   - Whisper 语音识别（模型缓存复用）
  lrc_writer.py   - LRC 歌词文件写入
  gui.py          - Tkinter 图形界面
  main.py         - 程序入口
"""
