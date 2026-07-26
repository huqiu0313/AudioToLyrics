"""应用数据目录解析：源码运行写项目目录，打包运行写 %APPDATA%"""

import os
import sys
from pathlib import Path


def is_frozen() -> bool:
    """是否以 PyInstaller 打包形式运行"""
    return getattr(sys, "frozen", False)


def app_data_dir() -> Path:
    """
    可写的应用数据目录（logs/、user_settings.json、tools/ 的父目录）。

    - 源码运行：项目根目录（现状不变）
    - 打包运行：%APPDATA%/AudioToLyrics（Program Files 只读，必须重定向）
    """
    if is_frozen():
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "AudioToLyrics"
    return Path(__file__).resolve().parent.parent
