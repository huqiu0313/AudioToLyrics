"""进度面板：进度条、批量进度、日志、开始/停止按钮"""

import customtkinter as ctk

from gui import styles as S


class ProgressPanel(ctk.CTkFrame):
    """底部进度与日志面板"""

    def __init__(self, master, on_start=None, on_stop=None, on_exit=None, **kwargs):
        super().__init__(
            master,
            fg_color=S.BG_PANEL,
            corner_radius=S.CORNER_RADIUS,
            **kwargs,
        )
        self._on_start = on_start
        self._on_stop = on_stop
        self._on_exit = on_exit
        self._build_ui()

    # ── 公开接口 ──────────────────────────────────────────────────────────────

    def update_progress(self, percent: int) -> None:
        self._progress_bar.set(percent / 100.0)
        self._progress_label.configure(text=f"{percent}%")

    def update_batch(self, current: int, total: int) -> None:
        self._batch_label.configure(text=f"批量进度: {current}/{total}")

    def append_log(self, text: str) -> None:
        self._log_text.configure(state="normal")
        self._log_text.insert("end", text + "\n")
        self._log_text.see("end")
        self._log_text.configure(state="disabled")

    def set_running(self, running: bool) -> None:
        """切换按钮状态：处理中时禁用开始、启用停止"""
        self._start_btn.configure(state="disabled" if running else "normal")
        self._stop_btn.configure(state="normal" if running else "disabled")

    # ── 内部 UI 构建 ──────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        pad = S.PAD_INNER

        # ── 按钮行（先打包到底部，确保始终可见）──
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(side="bottom", fill="x", padx=pad, pady=(S.PAD_BETWEEN, pad))

        self._start_btn = ctk.CTkButton(
            btn_row, text="▶ 开始处理", width=140,
            command=self._handle_start, **S.PRIMARY_BTN(),
        )
        self._start_btn.pack(side="left", padx=(0, 10))

        self._stop_btn = ctk.CTkButton(
            btn_row, text="■ 停止", width=100,
            command=self._handle_stop, state="disabled", **S.DANGER_BTN(),
        )
        self._stop_btn.pack(side="left", padx=(0, 10))

        self._exit_btn = ctk.CTkButton(
            btn_row, text="✕ 退出", width=100,
            command=self._handle_exit, **S.SECONDARY_BTN(),
        )
        self._exit_btn.pack(side="right")

        # ── 标题行 + 批量进度（醒目显示）──
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=pad, pady=(pad, 0))
        ctk.CTkLabel(top, text="📊 处理进度", font=S.get_font_heading(), text_color=S.FG_PRIMARY).pack(side="left")
        self._batch_label = ctk.CTkLabel(
            top, text="批量进度: 0/0", font=S.get_font_heading(), text_color=S.FG_ACCENT
        )
        self._batch_label.pack(side="right")

        # ── 进度条行（加粗）──
        bar_row = ctk.CTkFrame(self, fg_color="transparent")
        bar_row.pack(fill="x", padx=pad, pady=(S.PAD_BETWEEN, 0))
        self._progress_bar = ctk.CTkProgressBar(bar_row, height=18, corner_radius=9)
        self._progress_bar.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self._progress_bar.set(0)
        self._progress_label = ctk.CTkLabel(
            bar_row, text="0%", font=S.get_font_body(), text_color=S.FG_ACCENT, width=44
        )
        self._progress_label.pack(side="right")

        # ── 日志区（填充剩余空间，内容多时可滚动）──
        log_frame = ctk.CTkFrame(self, fg_color=S.BG_INPUT, corner_radius=6)
        log_frame.pack(fill="both", expand=True, padx=pad, pady=(S.PAD_BETWEEN, 0))
        self._log_text = ctk.CTkTextbox(
            log_frame,
            font=S.get_font_mono(),
            text_color=S.FG_PRIMARY,
            fg_color=S.BG_INPUT,
            state="disabled",
            wrap="word",
        )
        self._log_text.pack(fill="both", expand=True, padx=4, pady=4)

    def _handle_start(self) -> None:
        if self._on_start:
            self._on_start()

    def _handle_stop(self) -> None:
        if self._on_stop:
            self._on_stop()

    def _handle_exit(self) -> None:
        if self._on_exit:
            self._on_exit()
        else:
            self.winfo_toplevel().destroy()
