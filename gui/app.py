"""主窗口：组装所有面板，协调各组件，启动批量处理"""

import customtkinter as ctk

from config import (
    WINDOW_TITLE, WINDOW_WIDTH, WINDOW_HEIGHT,
    WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT,
)
from gui import styles as S
from gui.file_panel import FilePanel
from gui.settings_panel import SettingsPanel
from gui.progress_panel import ProgressPanel
from utils.settings_store import load_settings, save_settings
from utils.thread_worker import BatchWorker
from core.pipeline import process_file

# 批处理状态 → (文件列表显示文本, 列表状态级别, 日志级别)
_STATUS_DISPLAY: dict[str, tuple[str | None, str | None, str]] = {
    "processing": ("处理中...", "processing", "processing"),
    "done": ("完成", "success", "success"),
    "failed": ("失败", "error", "error"),
    "cancelled": ("已取消", "processing", "processing"),
    "all_done": (None, None, "success"),
}

# 批处理状态 → 日志图标
_STATUS_ICON = {
    "processing": "⏳",
    "done": "✅",
    "failed": "❌",
    "cancelled": "⛔",
    "all_done": "🎉",
}


class App(ctk.CTk):
    """AudioToLyrics 主应用窗口"""

    def __init__(self):
        super().__init__()
        self._worker: BatchWorker | None = None
        self._success_paths: set[str] = set()
        self._setup_window()
        self._build_layout()
        # 回填上次保存的设置（主题之外的设置面板各项）
        self._settings_panel.apply_settings(self._saved_settings)

    # ── 窗口配置 ──────────────────────────────────────────────────────────────

    def _setup_window(self) -> None:
        self._saved_settings = load_settings()
        appearance = self._saved_settings.get("appearance", "System")
        if appearance not in S.APPEARANCE_MODES.values():
            appearance = "System"
        self._appearance = appearance
        ctk.set_appearance_mode(appearance)
        ctk.set_default_color_theme(S.COLOR_THEME)
        self.title(WINDOW_TITLE)
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.configure(fg_color=S.BG_MAIN)

    # ── 布局组装 ──────────────────────────────────────────────────────────────

    def _build_layout(self) -> None:
        pad = S.PAD_OUTER

        # 顶部标题栏
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.pack(fill="x", padx=pad, pady=(pad, 0))
        ctk.CTkLabel(
            title_frame,
            text=f"🎵 {WINDOW_TITLE}",
            font=S.get_font_title(),
            text_color=S.FG_PRIMARY,
        ).pack(side="left")
        ctk.CTkLabel(
            title_frame,
            text="联网搜索，Demucs + Whisper 智能歌词识别",
            font=S.get_font_small(),
            text_color=S.FG_SECONDARY,
        ).pack(side="left", padx=(16, 0))

        # 主题切换（跟随系统/浅色/深色）
        self._appearance_button = ctk.CTkSegmentedButton(
            title_frame,
            values=list(S.APPEARANCE_MODES.keys()),
            command=self._on_appearance_change,
            font=S.get_font_body(),
        )
        self._appearance_button.pack(side="right")
        saved_label = S.APPEARANCE_LABELS.get(
            self._appearance, S.DEFAULT_APPEARANCE_LABEL
        )
        self._appearance_button.set(saved_label)

        # 主容器（grid 布局）
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=pad, pady=(pad // 2, pad))
        main_frame.rowconfigure(0, weight=2)
        main_frame.rowconfigure(1, weight=3)
        main_frame.columnconfigure(0, weight=3)

        # ── 上半区：文件面板 + 设置面板 ──
        top_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        top_frame.grid(row=0, column=0, sticky="nsew", pady=(0, pad // 2))
        top_frame.columnconfigure(0, weight=3)
        top_frame.columnconfigure(1, weight=2)
        top_frame.rowconfigure(0, weight=1)

        self._file_panel = FilePanel(top_frame)
        self._file_panel.grid(row=0, column=0, sticky="nsew", padx=(0, pad // 2))

        self._settings_panel = SettingsPanel(top_frame)
        self._settings_panel.grid(row=0, column=1, sticky="nsew", padx=(pad // 2, 0))

        # ── 下半区：进度面板 ──
        bottom_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        bottom_frame.grid(row=1, column=0, sticky="nsew", pady=(pad // 2, 0))

        self._progress_panel = ProgressPanel(
            bottom_frame,
            on_start=self._start_processing,
            on_stop=self._stop_processing,
            on_exit=self._exit,
        )
        self._progress_panel.pack(fill="both", expand=True)

    # ── 主题切换与设置持久化 ─────────────────────────────────────────────────

    def _on_appearance_change(self, label: str) -> None:
        self._appearance = S.APPEARANCE_MODES.get(label, "System")
        ctk.set_appearance_mode(self._appearance)
        self._persist_settings()

    def _persist_settings(self) -> None:
        """持久化主题 + 设置面板全部配置项"""
        save_settings({
            "appearance": self._appearance,
            **self._settings_panel.get_config(),
        })

    # ── 处理逻辑 ──────────────────────────────────────────────────────────────

    def _start_processing(self) -> None:
        files = self._file_panel.get_files()
        if not files:
            self._progress_panel.append_log("[提示] 请先添加音频文件")
            return

        config = self._settings_panel.get_config()
        self._persist_settings()
        self._progress_panel.set_running(True)
        self._progress_panel.append_log(f"[开始] 共 {len(files)} 个文件待处理")
        self._success_paths = set()

        def _on_progress(file_index, total, percent, message, status):
            # 在主线程中更新 UI（通过 after 调度）
            self.after(0, lambda: self._handle_progress(file_index, total, percent, message, status))

        self._worker = BatchWorker(
            file_list=files,
            process_func=process_file,
            progress_callback=_on_progress,
            config=config,
        )
        self._worker.start()

    def _stop_processing(self) -> None:
        if self._worker:
            self._worker.stop()
            self._progress_panel.append_log("[停止] 正在停止处理...")
            self._progress_panel.set_running(False)

    def _exit(self) -> None:
        """退出应用：保存设置，停止正在运行的任务，再关闭窗口"""
        self._persist_settings()
        if self._worker:
            self._worker.stop()
        self.destroy()

    def _handle_progress(self, file_index: int, total: int, percent: int, message: str, status: str) -> None:
        # 当前文件进度 + 总进度（单调递增）
        self._progress_panel.update_progress(percent)
        self._progress_panel.update_overall(file_index, total, percent)

        # 日志（图标 + 按级别着色）
        icon = _STATUS_ICON.get(status, "•")
        _, _, log_level = _STATUS_DISPLAY.get(status, (None, None, "info"))
        self._progress_panel.append_log(
            f"[{file_index}/{total}] {icon} {message}", level=log_level
        )

        # 文件列表状态（path 键控，按级别着色）
        display_text, level, _ = _STATUS_DISPLAY.get(status, (None, None, "info"))
        if display_text and self._worker and 0 < file_index <= len(self._worker.file_list):
            path = self._worker.file_list[file_index - 1]
            self._file_panel.set_file_status(path, display_text, level)

        # 记录成功的文件路径
        if status == "done" and self._worker:
            idx = file_index - 1
            if 0 <= idx < len(self._worker.file_list):
                self._success_paths.add(self._worker.file_list[idx])

        # 全部完成时：移除成功文件、恢复按钮
        if status in ("all_done", "cancelled"):
            self._file_panel.remove_paths(self._success_paths)
            self._progress_panel.set_running(False)
