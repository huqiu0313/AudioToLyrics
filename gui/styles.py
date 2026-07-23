"""GUI 统一样式常量：颜色、字体、间距、按钮样式（字体延迟初始化）"""

import customtkinter as ctk

# ── 全局主题 ──────────────────────────────────────────────────────────────────
APPEARANCE = "dark"           # "dark" | "light" | "system"
COLOR_THEME = "blue"          # "blue" | "green" | "dark-blue"

# ── 颜色 ──────────────────────────────────────────────────────────────────────
BG_MAIN = "#1e1e2e"           # 主背景（深色）
BG_PANEL = "#2a2a3d"          # 面板背景
BG_INPUT = "#363650"          # 输入框/下拉框背景
FG_PRIMARY = "#e4e4f0"        # 主文字颜色
FG_SECONDARY = "#9999b8"      # 次要文字/提示
FG_ACCENT = "#6c8cff"         # 强调色（按钮、链接）
FG_SUCCESS = "#4ade80"        # 成功状态
FG_WARNING = "#fbbf24"        # 警告/处理中状态
FG_ERROR = "#f87171"          # 错误/失败状态
FG_DISABLED = "#555570"       # 禁用状态

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
