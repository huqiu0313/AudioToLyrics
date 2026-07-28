"""主窗口：组装所有面板，协调各组件，启动批量处理"""

import threading

import customtkinter as ctk

from config import WINDOW_TITLE, WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT
from gui import styles as S
from gui.file_panel import FilePanel
from gui.settings_panel import SettingsPanel
from gui.progress_panel import ProgressPanel
from utils.thread_worker import BatchWorker
from core.pipeline import process_file
from core.artist_image import fetch_artist_images


class App(ctk.CTk):
    """AudioToLyrics v5 主应用窗口"""

    def __init__(self):
        super().__init__()
        self._worker: BatchWorker | None = None
        self._setup_window()
        self._build_layout()

    # ── 窗口配置 ──────────────────────────────────────────────────────────────

    def _setup_window(self) -> None:
        # 加载并应用用户主题
        theme_name = S.load_theme()
        S.apply_theme(theme_name)

        ctk.set_appearance_mode(S.APPEARANCE)
        ctk.set_default_color_theme(S.COLOR_THEME)
        self.title(WINDOW_TITLE)
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.configure(fg_color=S.BG_MAIN)

    # ── 布局组装（左右分栏）────────────────────────────────────────────────────

    def _build_layout(self) -> None:
        pad = S.PAD_OUTER

        # 顶部标题栏
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.pack(fill="x", padx=pad, pady=(pad, 0))
        ctk.CTkLabel(
            title_frame,
            text="🎵 AudioToLyrics v5",
            font=S.get_font_title(),
            text_color=S.FG_PRIMARY,
        ).pack(side="left")
        ctk.CTkLabel(
            title_frame,
            text="联网搜索 · Demucs + Whisper · 歌手头像",
            font=S.get_font_small(),
            text_color=S.FG_SECONDARY,
        ).pack(side="left", padx=(16, 0))

        # 右上角主题切换
        self._theme_var = ctk.StringVar(value="暗色" if S.load_theme() == "dark" else "亮色")
        ctk.CTkOptionMenu(
            title_frame,
            values=["暗色", "亮色"],
            variable=self._theme_var,
            font=S.get_font_small(),
            width=80,
            height=28,
            fg_color=S.BG_INPUT,
            button_color=S.FG_ACCENT,
            button_hover_color=S.FG_ACCENT,
            text_color=S.FG_PRIMARY,
            dropdown_fg_color=S.BG_PANEL,
            dropdown_text_color=S.FG_PRIMARY,
            dropdown_hover_color=S.BG_INPUT,
            command=self._on_theme_change,
        ).pack(side="right")
        ctk.CTkLabel(
            title_frame,
            text="主题重启后生效",
            font=S.get_font_small(),
            text_color=S.FG_SECONDARY,
        ).pack(side="right", padx=(0, 8))

        # 主容器（grid 布局：左列 + 右列）
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=pad, pady=(pad // 2, pad))
        main_frame.columnconfigure(0, weight=3)   # 左列
        main_frame.columnconfigure(1, weight=2)   # 右列
        main_frame.rowconfigure(0, weight=1)

        # ── 左列：文件面板（上）+ 进度面板（下）──
        left_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, pad // 2))
        left_frame.rowconfigure(0, weight=2)   # 文件面板
        left_frame.rowconfigure(1, weight=3)   # 进度面板
        left_frame.columnconfigure(0, weight=1)

        self._file_panel = FilePanel(left_frame)
        self._file_panel.grid(row=0, column=0, sticky="nsew", pady=(0, pad // 2))

        self._progress_panel = ProgressPanel(
            left_frame,
            on_start=self._start_processing,
            on_stop=self._stop_processing,
            on_exit=self._exit,
        )
        self._progress_panel.grid(row=1, column=0, sticky="nsew", pady=(pad // 2, 0))

        # ── 右列：设置面板（全高）──
        self._settings_panel = SettingsPanel(
            main_frame,
            on_artist_scan=self._start_artist_scan,
        )
        self._settings_panel.grid(row=0, column=1, sticky="nsew", padx=(pad // 2, 0))

    # ── 主题切换 ──────────────────────────────────────────────────────────────

    def _on_theme_change(self, value: str) -> None:
        theme_name = "dark" if value == "暗色" else "light"
        S.save_theme(theme_name)

    # ── 歌手头像扫描 ──────────────────────────────────────────────────────────

    def _start_artist_scan(self, folder: str) -> None:
        """在后台线程中执行歌手头像扫描，进度输出到日志区"""
        self._progress_panel.append_log(f"[歌手头像] 开始扫描: {folder}")

        def _run():
            def _on_progress(percent: int, message: str):
                self.after(0, lambda: self._progress_panel.append_log(f"[歌手头像] {message}"))

            try:
                result = fetch_artist_images(folder, progress_callback=_on_progress)
                summary = (
                    f"[歌手头像] 完成 — 成功: {len(result['success'])}, "
                    f"跳过: {len(result['skipped'])}, "
                    f"失败: {len(result['failed'])}"
                )
                self.after(0, lambda: self._progress_panel.append_log(summary))
            except Exception as e:
                self.after(0, lambda: self._progress_panel.append_log(f"[歌手头像] 错误: {e}"))

        t = threading.Thread(target=_run, daemon=True)
        t.start()

    # ── 处理逻辑 ──────────────────────────────────────────────────────────────

    def _start_processing(self) -> None:
        files = self._file_panel.get_files()
        if not files:
            self._progress_panel.append_log("[提示] 请先添加音频文件")
            return

        config = self._settings_panel.get_config()
        self._progress_panel.set_running(True)
        self._progress_panel.append_log(f"[开始] 共 {len(files)} 个文件待处理")
        self._success_paths: set[str] = set()

        def _on_progress(file_index, total, percent, message, status):
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
        """退出应用：先停止正在运行的任务，再关闭窗口"""
        if self._worker:
            self._worker.stop()
        self.destroy()

    def _handle_progress(self, file_index: int, total: int, percent: int, message: str, status: str) -> None:
        # 更新进度条和批量计数
        self._progress_panel.update_progress(percent)
        self._progress_panel.update_batch(file_index, total)

        # 更新日志
        status_icon = {
            "processing": "⏳",
            "done": "✅",
            "failed": "❌",
            "cancelled": "⛔",
            "all_done": "🎉",
        }.get(status, "•")
        self._progress_panel.append_log(f"[{file_index}/{total}] {status_icon} {message}")

        # 更新文件列表状态
        display_status = {
            "processing": "处理中...",
            "done": "完成",
            "failed": "失败",
            "cancelled": "已取消",
        }.get(status, "")
        if display_status:
            self._file_panel.set_file_status(file_index, display_status)

        # 记录成功的文件路径
        if status == "done" and self._worker:
            idx = file_index - 1
            if 0 <= idx < len(self._worker.file_list):
                self._success_paths.add(self._worker.file_list[idx])

        # 全部完成时：移除成功文件、恢复按钮
        if status in ("all_done", "cancelled"):
            self._file_panel.remove_paths(self._success_paths)
            self._progress_panel.set_running(False)
