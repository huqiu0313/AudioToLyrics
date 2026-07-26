"""进度面板：总进度 + 当前文件双进度条、分级着色日志、开始/停止/退出按钮"""

import customtkinter as ctk

from gui import styles as S

# 需要着色的日志级别（info 使用默认文字色，不配 tag）
_LOG_TAG_LEVELS = ("processing", "success", "error")


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
        self._refresh_log_tags()
        # tk 原生 tag 不吃 CTk 双色元组，主题切换时需手动重刷
        S.on_theme_change(self._refresh_log_tags)

    # ── 公开接口 ──────────────────────────────────────────────────────────────

    def update_progress(self, percent: int) -> None:
        """更新"当前文件"进度条"""
        self._file_bar.set(percent / 100.0)
        self._file_label.configure(text=f"{percent}%")

    def update_overall(self, file_index: int, total: int, file_percent: int) -> None:
        """更新总进度（换文件时单调递增不回跳）与批量计数"""
        if total > 0:
            overall = ((file_index - 1) + file_percent / 100.0) / total
        else:
            overall = 0.0
        overall = min(max(overall, 0.0), 1.0)
        self._overall_bar.set(overall)
        self._overall_label.configure(text=f"{int(overall * 100)}%")
        self._batch_label.configure(text=f"批量进度: {file_index}/{total}")

    def append_log(self, text: str, level: str = "info") -> None:
        """追加日志并按级别着色（level: info / processing / success / error）"""
        tag = level if level in _LOG_TAG_LEVELS else None
        self._log_text.configure(state="normal")
        self._log_text.insert("end", text + "\n", tag)
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

        self._start_btn = S.make_button(
            btn_row, "▶ 开始处理", self._handle_start, style="primary"
        )
        self._start_btn.pack(side="left", padx=(0, 10))

        self._stop_btn = S.make_button(
            btn_row, "■ 停止", self._handle_stop, style="danger",
            width=S.BTN_WIDTH_SM, state="disabled",
        )
        self._stop_btn.pack(side="left", padx=(0, 10))

        self._exit_btn = S.make_button(
            btn_row, "✕ 退出", self._handle_exit, style="secondary",
            width=S.BTN_WIDTH_SM,
        )
        self._exit_btn.pack(side="right")

        # ── 标题行 + 批量进度 ──
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=pad, pady=(pad, 0))
        ctk.CTkLabel(top, text="📊 处理进度", font=S.get_font_heading(), text_color=S.FG_PRIMARY).pack(side="left")
        self._batch_label = ctk.CTkLabel(
            top, text="批量进度: 0/0", font=S.get_font_small(), text_color=S.FG_SECONDARY
        )
        self._batch_label.pack(side="right")

        # ── 总进度条（单调递增）──
        self._overall_bar, self._overall_label = self._build_bar_row(
            caption="总进度", pady=(S.PAD_BETWEEN, 0)
        )

        # ── 当前文件进度条 ──
        self._file_bar, self._file_label = self._build_bar_row(
            caption="当前文件", pady=(4, 0)
        )

        # ── 日志区（填充剩余空间，内容多时可滚动）──
        log_frame = ctk.CTkFrame(self, fg_color=S.BG_INPUT, corner_radius=S.CORNER_RADIUS_SM)
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

    def _build_bar_row(self, caption: str, pady: tuple) -> tuple:
        """构建一行：标题 + 进度条 + 百分比，返回 (bar, percent_label)"""
        pad = S.PAD_INNER
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=pad, pady=pady)
        ctk.CTkLabel(
            row, text=caption, font=S.get_font_small(),
            text_color=S.FG_SECONDARY, width=56, anchor="w",
        ).pack(side="left", padx=(0, 6))
        bar = ctk.CTkProgressBar(row, height=12, corner_radius=S.CORNER_RADIUS_SM)
        bar.pack(side="left", fill="x", expand=True, padx=(0, 10))
        bar.set(0)
        label = ctk.CTkLabel(
            row, text="0%", font=S.get_font_small(), text_color=S.FG_ACCENT, width=40
        )
        label.pack(side="right")
        return bar, label

    def _refresh_log_tags(self) -> None:
        """用当前主题颜色重配日志 tag（tag 为引用，历史文本自动整体变色）"""
        self._log_text.tag_config("processing", foreground=S.resolve(S.FG_WARNING))
        self._log_text.tag_config("success", foreground=S.resolve(S.FG_SUCCESS))
        self._log_text.tag_config("error", foreground=S.resolve(S.FG_ERROR))

    # ── 按钮事件 ──────────────────────────────────────────────────────────────

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
