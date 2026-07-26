"""用户设置持久化：user_settings.json（原子写入，损坏容错）"""

import json
import os

from utils.logging_setup import get_logger
from utils.paths import app_data_dir

logger = get_logger(__name__)

_SETTINGS_PATH = app_data_dir() / "user_settings.json"


def load_settings() -> dict:
    """读取用户设置；文件不存在或损坏时返回空 dict（全默认值）"""
    try:
        with open(_SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
        logger.warning("设置文件格式异常（非 JSON 对象），使用默认设置")
    except FileNotFoundError:
        pass
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("设置文件读取失败，使用默认设置: %s", e)
    return {}


def save_settings(settings: dict) -> None:
    """原子写入用户设置（先写临时文件再替换，防止半截文件）"""
    tmp_path = _SETTINGS_PATH.with_suffix(".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, _SETTINGS_PATH)
    except OSError as e:
        logger.warning("设置保存失败: %s", e)
