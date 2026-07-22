"""设置面板：Whisper/Demucs 模型选择、歌词来源、功能开关"""

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
            "auto_convert_video": self._auto_convert_var.get(),
            "use_demucs": self._use_demucs_var.get(),
            "use_whisper": self._use_whisper_var.get(),
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
            font=S.get_font_body(), text_color=S.FG_ACCENT,
        ).pack(anchor="w", padx=pad, pady=(0, S.PAD_SECTION))

        # ── 功能开关 ──────────────────────────────────────────────────────
        ctk.CTkLabel(
            scroll, text="功能开关", font=S.get_font_body(), text_color=S.FG_SECONDARY
        ).pack(anchor="w", padx=pad)

        # 视频自动转音频
        self._auto_convert_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            scroll,
            text="识别到视频则自动转为音频",
            variable=self._auto_convert_var,
            font=S.get_font_body(),
            text_color=S.FG_PRIMARY,
            fg_color=S.FG_ACCENT,
        ).pack(anchor="w", padx=pad + 10, pady=(4, 0))

        # 分割线
        ctk.CTkFrame(scroll, fg_color=S.BG_INPUT, height=1).pack(fill="x", padx=pad, pady=(S.PAD_BETWEEN, S.PAD_BETWEEN))

        # 启用 Demucs
        self._use_demucs_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            scroll,
            text="启用 Demucs 人声分离",
            variable=self._use_demucs_var,
            font=S.get_font_body(),
            text_color=S.FG_PRIMARY,
            fg_color=S.FG_ACCENT,
            command=self._on_demucs_toggle,
        ).pack(anchor="w", padx=pad + 10, pady=(4, 0))
        ctk.CTkLabel(
            scroll,
            text="ℹ️ 需要下载模型，分离可大大提升识别准确率",
            font=S.get_font_small(), text_color=S.FG_WARNING,
        ).pack(anchor="w", padx=pad + 10)

        # Demucs 模型下拉
        self._demucs_var = ctk.StringVar(value=DEFAULT_DEMUCS_MODEL)
        self._demucs_dropdown = self._add_dropdown(
            scroll, "Demucs 模型", DEMUCS_MODELS, self._demucs_var, disabled=True
        )

        # 启用 Whisper
        self._use_whisper_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            scroll,
            text="启用 Whisper 语音识别",
            variable=self._use_whisper_var,
            font=S.get_font_body(),
            text_color=S.FG_PRIMARY,
            fg_color=S.FG_ACCENT,
            command=self._on_whisper_toggle,
        ).pack(anchor="w", padx=pad + 10, pady=(S.PAD_BETWEEN, 0))
        ctk.CTkLabel(
            scroll,
            text="ℹ️ 需要下载模型，语音识别可能不准确",
            font=S.get_font_small(), text_color=S.FG_WARNING,
        ).pack(anchor="w", padx=pad + 10)

        # Whisper 模型下拉
        self._whisper_var = ctk.StringVar(value=DEFAULT_WHISPER_MODEL)
        self._whisper_dropdown = self._add_dropdown(
            scroll, "Whisper 模型", WHISPER_MODELS, self._whisper_var, disabled=True
        )

        # 分割线
        ctk.CTkFrame(scroll, fg_color=S.BG_INPUT, height=1).pack(fill="x", padx=pad, pady=S.PAD_SECTION)

        # 歌词来源勾选框
        ctk.CTkLabel(
            scroll, text="联网搜索来源", font=S.get_font_small(), text_color=S.FG_SECONDARY
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

    # ── 下拉框启用/禁用联动 ────────────────────────────────────────────────

    def _on_demucs_toggle(self) -> None:
        state = "normal" if self._use_demucs_var.get() else "disabled"
        self._demucs_dropdown.configure(state=state)

    def _on_whisper_toggle(self) -> None:
        state = "normal" if self._use_whisper_var.get() else "disabled"
        self._whisper_dropdown.configure(state=state)

    def _add_dropdown(
        self, parent, label: str, values: tuple, variable: ctk.StringVar,
        disabled: bool = False,
    ) -> ctk.CTkOptionMenu:
        pad = S.PAD_INNER
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=pad, pady=(S.PAD_BETWEEN, 0))
        ctk.CTkLabel(frame, text=label, font=S.get_font_small(), text_color=S.FG_SECONDARY).pack(anchor="w")
        dropdown = ctk.CTkOptionMenu(
            frame,
            values=list(values),
            variable=variable,
            font=S.get_font_body(),
            height=S.INPUT_HEIGHT,
            fg_color=S.BG_INPUT,
            button_color=S.FG_ACCENT,
            state="disabled" if disabled else "normal",
        )
        dropdown.pack(fill="x", pady=(2, 0))
        return dropdown

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
