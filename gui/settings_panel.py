"""设置面板：Whisper/Demucs 模型选择、歌词来源、功能开关、解密设置"""

import customtkinter as ctk
from tkinter import filedialog

from gui import styles as S
from config import (
    WHISPER_MODELS, DEFAULT_WHISPER_MODEL,
    DEMUCS_MODELS, DEFAULT_DEMUCS_MODEL,
    LYRICS_PROVIDERS, LYRICS_PROVIDER_LABELS,
)
from utils.deps import has_demucs, has_whisper
from utils.logging_setup import get_logger

logger = get_logger(__name__)


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
            "decrypt_output_dir": self._decrypt_dir_var.get().strip(),
            "delete_source_after_convert": self._delete_source_var.get(),
        }

    def apply_settings(self, d: dict) -> None:
        """从持久化 dict 回填设置（缺项/非法值保持默认）"""
        if not d:
            return

        if d.get("whisper_model") in WHISPER_MODELS:
            self._whisper_var.set(d["whisper_model"])
        if d.get("demucs_model") in DEMUCS_MODELS:
            self._demucs_var.set(d["demucs_model"])

        providers = d.get("providers")
        if isinstance(providers, list):
            for key, var in self._provider_vars.items():
                var.set(key in providers)

        for key, var in (
            ("auto_convert_video", self._auto_convert_var),
            ("use_demucs", self._use_demucs_var),
            ("use_whisper", self._use_whisper_var),
            ("delete_source_after_convert", self._delete_source_var),
        ):
            if isinstance(d.get(key), bool):
                var.set(d[key])

        if isinstance(d.get("decrypt_output_dir"), str):
            self._decrypt_dir_var.set(d["decrypt_output_dir"])

        # 安装版无 AI 组件：忽略持久化中的启用状态
        if not self._demucs_available:
            self._use_demucs_var.set(False)
        if not self._whisper_available:
            self._use_whisper_var.set(False)

        # 刷新下拉框启用/禁用联动
        self._on_demucs_toggle()
        self._on_whisper_toggle()

    # ── 内部 UI 构建 ──────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        pad = S.PAD_INNER

        # AI 组件可用性（安装版未打包，对应选项禁用）
        self._demucs_available = has_demucs()
        self._whisper_available = has_whisper()

        # 使用可滚动容器，防止内容被裁剪
        scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent", scrollbar_button_color=S.BG_INPUT
        )
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
        S.make_checkbox(
            scroll, "识别到视频则自动转为音频", self._auto_convert_var
        ).pack(anchor="w", padx=pad + 10, pady=(4, 0))

        # 转换后删除源文件
        self._delete_source_var = ctk.BooleanVar(value=False)
        S.make_checkbox(
            scroll, "转换后删除源文件（加密/视频）", self._delete_source_var
        ).pack(anchor="w", padx=pad + 10, pady=(4, 0))

        # 解密输出目录
        ctk.CTkLabel(
            scroll, text="解密输出目录（留空则输出到源文件同目录）",
            font=S.get_font_small(), text_color=S.FG_SECONDARY,
        ).pack(anchor="w", padx=pad + 10, pady=(S.PAD_BETWEEN, 2))
        dir_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        dir_frame.pack(fill="x", padx=pad + 10)
        self._decrypt_dir_var = ctk.StringVar(value="")
        ctk.CTkEntry(
            dir_frame,
            textvariable=self._decrypt_dir_var,
            placeholder_text="留空 = 源文件同目录",
            font=S.get_font_body(),
            fg_color=S.BG_INPUT,
            height=S.INPUT_HEIGHT,
        ).pack(side="left", fill="x", expand=True)
        S.make_button(
            dir_frame, "浏览", self._browse_decrypt_dir,
            style="secondary", width=S.BTN_WIDTH_XS,
        ).pack(side="left", padx=(6, 0))

        # 分割线
        S.make_divider(scroll).pack(fill="x", padx=pad, pady=S.PAD_BETWEEN)

        # 启用 Demucs
        self._use_demucs_var = ctk.BooleanVar(value=False)
        demucs_state = "normal" if self._demucs_available else "disabled"
        S.make_checkbox(
            scroll, "启用 Demucs 人声分离", self._use_demucs_var,
            command=self._on_demucs_toggle, state=demucs_state,
        ).pack(anchor="w", padx=pad + 10, pady=(4, 0))
        if self._demucs_available:
            demucs_hint = "ℹ️ 需要下载模型，分离可大大提升识别准确率"
            demucs_hint_color = S.FG_WARNING
        else:
            demucs_hint = "安装版未包含 Demucs 组件（源码版可 pip install -r requirements-ai.txt）"
            demucs_hint_color = S.FG_DISABLED
        ctk.CTkLabel(
            scroll,
            text=demucs_hint,
            font=S.get_font_small(), text_color=demucs_hint_color,
        ).pack(anchor="w", padx=pad + 10)

        # Demucs 模型下拉
        self._demucs_var = ctk.StringVar(value=DEFAULT_DEMUCS_MODEL)
        self._demucs_dropdown = self._add_dropdown(
            scroll, "Demucs 模型", DEMUCS_MODELS, self._demucs_var, disabled=True
        )

        # 启用 Whisper
        self._use_whisper_var = ctk.BooleanVar(value=False)
        whisper_state = "normal" if self._whisper_available else "disabled"
        S.make_checkbox(
            scroll, "启用 Whisper 语音识别", self._use_whisper_var,
            command=self._on_whisper_toggle, state=whisper_state,
        ).pack(anchor="w", padx=pad + 10, pady=(S.PAD_BETWEEN, 0))
        if self._whisper_available:
            whisper_hint = "ℹ️ 需要下载模型，语音识别可能不准确"
            whisper_hint_color = S.FG_WARNING
        else:
            whisper_hint = "安装版未包含 Whisper 组件（源码版可 pip install -r requirements-ai.txt）"
            whisper_hint_color = S.FG_DISABLED
        ctk.CTkLabel(
            scroll,
            text=whisper_hint,
            font=S.get_font_small(), text_color=whisper_hint_color,
        ).pack(anchor="w", padx=pad + 10)

        # Whisper 模型下拉
        self._whisper_var = ctk.StringVar(value=DEFAULT_WHISPER_MODEL)
        self._whisper_dropdown = self._add_dropdown(
            scroll, "Whisper 模型", WHISPER_MODELS, self._whisper_var, disabled=True
        )

        # 分割线
        S.make_divider(scroll).pack(fill="x", padx=pad, pady=S.PAD_SECTION)

        # 歌词来源勾选框
        ctk.CTkLabel(
            scroll, text="联网搜索来源", font=S.get_font_small(), text_color=S.FG_SECONDARY
        ).pack(anchor="w", padx=pad)
        self._provider_vars: dict[str, ctk.BooleanVar] = {}
        for key in LYRICS_PROVIDERS:
            var = ctk.BooleanVar(value=True)
            self._provider_vars[key] = var
            S.make_checkbox(scroll, LYRICS_PROVIDER_LABELS[key], var).pack(
                anchor="w", padx=pad + 10, pady=(2, 0)
            )

        # 底部分割线
        S.make_divider(scroll).pack(fill="x", padx=pad, pady=S.PAD_SECTION)

    # ── 目录浏览 ────────────────────────────────────────────────────────────

    def _browse_decrypt_dir(self) -> None:
        folder = filedialog.askdirectory(title="选择解密输出目录")
        if folder:
            self._decrypt_dir_var.set(folder)

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
            logger.debug("未安装 torch，计算设备按 cpu 处理")
            return "cpu（未安装 torch）"
