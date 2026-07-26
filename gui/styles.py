"""GUI 统一样式：明暗双主题颜色 token、字体、间距、控件工厂（字体延迟初始化）

颜色全部为 (浅色, 深色) 元组，CTk 控件直接消费，切换主题时自动重绘。
必须传单值颜色的 tk 原生场景（如 Textbox tag）使用 resolve()。
"""

import customtkinter as ctk

# ── 主题元数据 ──────────────────────────────────────────────────────────────
APPEARANCE_MODES = {"跟随系统": "System", "浅色": "Light", "深色": "Dark"}
APPEARANCE_LABELS = {v: k for k, v in APPEARANCE_MODES.items()}  # 反向映射
DEFAULT_APPEARANCE_LABEL = "跟随系统"
COLOR_THEME = "blue"          # "blue" | "green" | "dark-blue"

# ── 语义化颜色 token：(浅色, 深色) ────────────────────────────────────────────
BG_MAIN = ("#f5f6fa", "#1e1e2e")        # 主背景
BG_PANEL = ("#ffffff", "#2a2a3d")       # 面板背景
BG_INPUT = ("#e8eaf2", "#363650")       # 输入框/下拉框/日志背景
BORDER = ("#c9cddf", "#44445e")         # 边框/分割线
FG_PRIMARY = ("#1a1a2e", "#e4e4f0")     # 主文字
FG_SECONDARY = ("#5a5f7a", "#9999b8")   # 次要文字/提示
FG_ACCENT = ("#3b5bdb", "#6c8cff")      # 强调色（按钮、链接）
FG_ACCENT_HOVER = ("#2f4bc4", "#5570e6")
FG_SUCCESS = ("#1e9e4a", "#4ade80")     # 成功状态
FG_WARNING = ("#b97d0a", "#fbbf24")     # 警告/处理中状态
FG_ERROR = ("#d33f3f", "#f87171")       # 错误/失败状态
FG_ERROR_HOVER = ("#b82f2f", "#e04040")
FG_DISABLED = ("#9aa0b5", "#555570")    # 禁用状态
TEXT_ON_ACCENT = ("#ffffff", "#ffffff")  # 强调色按钮上的文字

# 状态级别 → 颜色（文件状态列与日志区共用同一映射）
LEVEL_COLORS = {
    "pending": FG_SECONDARY,
    "processing": FG_WARNING,
    "success": FG_SUCCESS,
    "error": FG_ERROR,
    "info": FG_PRIMARY,
}


def resolve(color) -> str:
    """将 (浅色, 深色) 元组解析为当前模式下的单值颜色（仅供 tk 原生场景）"""
    if isinstance(color, str):
        return color
    return color[0] if ctk.get_appearance_mode() == "Light" else color[1]


def on_theme_change(callback) -> None:
    """订阅主题变更（供必须手动重刷的 tk 原生部分注册，如 Textbox tag）"""
    ctk.AppearanceModeTracker.add(callback)


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
BTN_WIDTH = 140         # 主按钮
BTN_WIDTH_SM = 100      # 次要按钮
BTN_WIDTH_XS = 50       # 浏览等小按钮
INPUT_HEIGHT = 32
CORNER_RADIUS = 8       # 面板/按钮圆角
CORNER_RADIUS_SM = 6    # 内嵌容器圆角

# ── 按钮样式快捷方式 ──────────────────────────────────────────────────────────


def _btn_style(fg, hover, text) -> dict:
    return {
        "fg_color": fg,
        "hover_color": hover,
        "text_color": text,
        "corner_radius": CORNER_RADIUS,
        "height": BTN_HEIGHT,
    }


def PRIMARY_BTN() -> dict:
    return _btn_style(FG_ACCENT, FG_ACCENT_HOVER, TEXT_ON_ACCENT)


def DANGER_BTN() -> dict:
    return _btn_style(FG_ERROR, FG_ERROR_HOVER, TEXT_ON_ACCENT)


def SECONDARY_BTN() -> dict:
    return _btn_style(BG_INPUT, BORDER, FG_PRIMARY)


_BUTTON_STYLES = {
    "primary": PRIMARY_BTN,
    "danger": DANGER_BTN,
    "secondary": SECONDARY_BTN,
}


# ── 控件工厂（消灭各面板重复的参数块）──────────────────────────────────────────


def make_button(
    parent,
    text: str,
    command,
    style: str = "primary",
    width: int = BTN_WIDTH,
    **kwargs,
) -> ctk.CTkButton:
    """创建统一风格的按钮，style: "primary" | "danger" | "secondary" """
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        width=width,
        font=get_font_body(),
        **_BUTTON_STYLES[style](),
        **kwargs,
    )


def make_checkbox(parent, text: str, variable, command=None, **kwargs) -> ctk.CTkCheckBox:
    """创建统一风格的复选框（**kwargs 透传，如 state="disabled"）"""
    return ctk.CTkCheckBox(
        parent,
        text=text,
        variable=variable,
        command=command,
        font=get_font_body(),
        text_color=FG_PRIMARY,
        fg_color=FG_ACCENT,
        hover_color=FG_ACCENT_HOVER,
        **kwargs,
    )


def make_divider(parent) -> ctk.CTkFrame:
    """创建 1px 分割线（pack 时 fill="x"）"""
    return ctk.CTkFrame(parent, height=1, fg_color=BORDER)
