"""
audio_to_lrc - 歌曲歌词识别器 v3.0
联网搜索获取歌词，对齐时间戳，生成 LRC 文件

模块结构:
  config.py       - 全局配置常量
  utils.py        - 工具函数（设备检测、文本清洗、时间格式化）
  separator.py    - Demucs 人声分离
  recognizer.py   - Whisper 语音识别（模型缓存复用）
  aligner.py      - 官方歌词与时间戳对齐
  web_search.py   - 官方歌词搜索与提取
  lrc_writer.py   - LRC 歌词文件写入
  gui.py          - Tkinter 图形界面
  main.py         - 程序入口
"""
