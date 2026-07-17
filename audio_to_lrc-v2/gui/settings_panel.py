"""设置面板：Whisper/Demucs 模型选择、歌词来源"""

import customtkinter as ctk

from gui import styles as S
from config import (
    WHISPER_MODELS, DEFAULT_WHISPER_MODEL,
    DEMUCS_MODELS, DEFAULT_DEMUCS_MODEL,
    LYRICS_PROVIDERS, LYRICS_PROVIDER_LABELS,
)


class SettingsPanel(ctk.CTkFrame):
    """右侧设置面板"""

    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            fg_color=S.BG_PANEL,
            corner_radius=S.CORNER_RADIUS,
            **kwargs,
        )
        self._build_ui()

    # ── 公开接口 ──────────────────────────────────────────────────────────────

    def get_config(self) -> dict:
        """返回当前所有设置的配置字典"""
        providers = [p for p, var in self._provider_vars.items() if var.get()]
        return {
            "whisper_model": self._whisper_var.get(),
            "demucs_model": self._demucs_var.get(),
            "providers": providers if providers else None,
        }

    # ── 内部 UI 构建 ──────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        pad = S.PAD_INNER

        # 使用可滚动容器，防止内容被裁剪
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", scrollbar_button_color=S.BG_INPUT)
        scroll.pack(fill="both", expand=True)

        # 标题
        ctk.CTkLabel(
            scroll, text="⚙ 处理设置", font=S.get_font_heading(), text_color=S.FG_PRIMARY
        ).pack(anchor="w", padx=pad, pady=(pad, S.PAD_SECTION))

        # 计算设备信息
        device_text = self._detect_device()
        ctk.CTkLabel(
            scroll, text=f"计算设备: {device_text}",
            font=S.get_font_small(), text_color=S.FG_ACCENT,
        ).pack(anchor="w", padx=pad, pady=(0, S.PAD_SECTION))

        # Whisper 模型
        self._whisper_var = ctk.StringVar(value=DEFAULT_WHISPER_MODEL)
        self._add_dropdown(scroll, "Whisper 模型", WHISPER_MODELS, self._whisper_var)

        # Demucs 模型
        self._demucs_var = ctk.StringVar(value=DEFAULT_DEMUCS_MODEL)
        self._add_dropdown(scroll, "Demucs 模型", DEMUCS_MODELS, self._demucs_var)

        # 分割线
        ctk.CTkFrame(scroll, fg_color=S.BG_INPUT, height=1).pack(fill="x", padx=pad, pady=S.PAD_SECTION)

        # 歌词来源勾选框
        ctk.CTkLabel(
            scroll, text="歌词搜索来源", font=S.get_font_small(), text_color=S.FG_SECONDARY
        ).pack(anchor="w", padx=pad)
        self._provider_vars: dict[str, ctk.BooleanVar] = {}
        for key in LYRICS_PROVIDERS:
            var = ctk.BooleanVar(value=True)
            self._provider_vars[key] = var
            ctk.CTkCheckBox(
                scroll,
                text=LYRICS_PROVIDER_LABELS[key],
                variable=var,
                font=S.get_font_body(),
                text_color=S.FG_PRIMARY,
                fg_color=S.FG_ACCENT,
            ).pack(anchor="w", padx=pad + 10, pady=(2, 0))

        # 分割线
        ctk.CTkFrame(scroll, fg_color=S.BG_INPUT, height=1).pack(fill="x", padx=pad, pady=S.PAD_SECTION)

    def _add_dropdown(self, parent, label: str, values: tuple, variable: ctk.StringVar) -> None:
        pad = S.PAD_INNER
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=pad, pady=(S.PAD_BETWEEN, 0))
        ctk.CTkLabel(frame, text=label, font=S.get_font_small(), text_color=S.FG_SECONDARY).pack(anchor="w")
        ctk.CTkOptionMenu(
            frame,
            values=list(values),
            variable=variable,
            font=S.get_font_body(),
            height=S.INPUT_HEIGHT,
            fg_color=S.BG_INPUT,
            button_color=S.FG_ACCENT,
        ).pack(fill="x", pady=(2, 0))

    @staticmethod
    def _detect_device() -> str:
        """检测计算设备，返回描述字符串"""
        try:
            import torch
            if torch.cuda.is_available():
                gpu_name = torch.cuda.get_device_name(0)
                return f"cuda（{gpu_name}）"
            return "cpu"
        except ImportError:
            return "cpu（未安装 torch）"
