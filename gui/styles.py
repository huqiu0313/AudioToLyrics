"""GUI 统一样式常量：颜色、字体、间距、按钮样式（支持亮/暗主题切换）"""

import json
from pathlib import Path

import customtkinter as ctk

# ── 用户设置文件路径 ──────────────────────────────────────────────────────────
_USER_SETTINGS_FILE = Path(__file__).resolve().parent.parent / "user_settings.json"

# ── 主题颜色方案 ──────────────────────────────────────────────────────────────

DARK_THEME = {
    "appearance": "dark",
    "color_theme": "blue",
    "BG_MAIN": "#1e1e2e",
    "BG_PANEL": "#2a2a3d",
    "BG_INPUT": "#363650",
    "FG_PRIMARY": "#e4e4f0",
    "FG_SECONDARY": "#9999b8",
    "FG_ACCENT": "#6c8cff",
    "FG_SUCCESS": "#4ade80",
    "FG_WARNING": "#fbbf24",
    "FG_ERROR": "#f87171",
    "FG_DISABLED": "#555570",
}

LIGHT_THEME = {
    "appearance": "light",
    "color_theme": "blue",
    "BG_MAIN": "#f0f0f5",
    "BG_PANEL": "#ffffff",
    "BG_INPUT": "#e4e4ec",
    "FG_PRIMARY": "#1a1a2e",
    "FG_SECONDARY": "#5c5c7a",
    "FG_ACCENT": "#4a6cf7",
    "FG_SUCCESS": "#16a34a",
    "FG_WARNING": "#d97706",
    "FG_ERROR": "#dc2626",
    "FG_DISABLED": "#a0a0b8",
}

_THEMES = {"dark": DARK_THEME, "light": LIGHT_THEME}

# ── 当前激活的颜色变量（模块级，供外部 import 使用）──────────────────────────
APPEARANCE = "dark"
COLOR_THEME = "blue"
BG_MAIN = DARK_THEME["BG_MAIN"]
BG_PANEL = DARK_THEME["BG_PANEL"]
BG_INPUT = DARK_THEME["BG_INPUT"]
FG_PRIMARY = DARK_THEME["FG_PRIMARY"]
FG_SECONDARY = DARK_THEME["FG_SECONDARY"]
FG_ACCENT = DARK_THEME["FG_ACCENT"]
FG_SUCCESS = DARK_THEME["FG_SUCCESS"]
FG_WARNING = DARK_THEME["FG_WARNING"]
FG_ERROR = DARK_THEME["FG_ERROR"]
FG_DISABLED = DARK_THEME["FG_DISABLED"]


def apply_theme(theme_name: str) -> None:
    """应用指定主题，更新模块级颜色变量"""
    global APPEARANCE, COLOR_THEME
    global BG_MAIN, BG_PANEL, BG_INPUT
    global FG_PRIMARY, FG_SECONDARY, FG_ACCENT
    global FG_SUCCESS, FG_WARNING, FG_ERROR, FG_DISABLED

    theme = _THEMES.get(theme_name, DARK_THEME)
    APPEARANCE = theme["appearance"]
    COLOR_THEME = theme["color_theme"]
    BG_MAIN = theme["BG_MAIN"]
    BG_PANEL = theme["BG_PANEL"]
    BG_INPUT = theme["BG_INPUT"]
    FG_PRIMARY = theme["FG_PRIMARY"]
    FG_SECONDARY = theme["FG_SECONDARY"]
    FG_ACCENT = theme["FG_ACCENT"]
    FG_SUCCESS = theme["FG_SUCCESS"]
    FG_WARNING = theme["FG_WARNING"]
    FG_ERROR = theme["FG_ERROR"]
    FG_DISABLED = theme["FG_DISABLED"]


def load_theme() -> str:
    """从 user_settings.json 读取主题设置，返回 'dark' 或 'light'"""
    try:
        if _USER_SETTINGS_FILE.exists():
            data = json.loads(_USER_SETTINGS_FILE.read_text(encoding="utf-8"))
            return data.get("theme", "dark")
    except Exception:
        pass
    return "dark"


def save_theme(theme_name: str) -> None:
    """将主题设置写入 user_settings.json"""
    data = {}
    try:
        if _USER_SETTINGS_FILE.exists():
            data = json.loads(_USER_SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    data["theme"] = theme_name
    _USER_SETTINGS_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ── 字体族名 ──────────────────────────────────────────────────────────────────
FONT_FAMILY = "Microsoft YaHei UI"  # 微软雅黑

# ── 字体（延迟初始化，需要 Tk root 存在后才能创建）──────────────────────────
_fonts: dict = {}


def _get_font(key: str, **kwargs) -> ctk.CTkFont:
    if key not in _fonts:
        _fonts[key] = ctk.CTkFont(**kwargs)
    return _fonts[key]


def get_font_title() -> ctk.CTkFont:
    return _get_font("title", family=FONT_FAMILY, size=18, weight="bold")


def get_font_heading() -> ctk.CTkFont:
    return _get_font("heading", family=FONT_FAMILY, size=14, weight="bold")


def get_font_body() -> ctk.CTkFont:
    return _get_font("body", family=FONT_FAMILY, size=12)


def get_font_small() -> ctk.CTkFont:
    return _get_font("small", family=FONT_FAMILY, size=10)


def get_font_mono() -> ctk.CTkFont:
    return _get_font("mono", family="Consolas", size=11)


# ── 间距 ──────────────────────────────────────────────────────────────────────
PAD_OUTER = 16          # 面板外边距
PAD_INNER = 10          # 面板内边距
PAD_BETWEEN = 8         # 控件间距
PAD_SECTION = 14        # 区块间距

# ── 控件尺寸 ──────────────────────────────────────────────────────────────────
BTN_HEIGHT = 36
BTN_WIDTH = 140
INPUT_HEIGHT = 32
CORNER_RADIUS = 8

# ── 按钮样式快捷方式（字体在运行时获取）───────────────────────────────────────


def _btn_style(fg, hover, text) -> dict:
    return {
        "fg_color": fg,
        "hover_color": hover,
        "text_color": text,
        "corner_radius": CORNER_RADIUS,
        "height": BTN_HEIGHT,
    }


def PRIMARY_BTN() -> dict:
    return _btn_style(FG_ACCENT, "#5570e6", "#ffffff")


def DANGER_BTN() -> dict:
    return _btn_style(FG_ERROR, "#e04040", "#ffffff")


def SECONDARY_BTN() -> dict:
    return _btn_style(BG_INPUT, "#4a4a6a", FG_PRIMARY)
