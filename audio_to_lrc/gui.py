"""
GUI 模块：Tkinter 界面
负责所有界面布局和交互逻辑
"""

import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import zhconv

from config import (
    APP_TITLE, APP_SUBTITLE, WINDOW_WIDTH, WINDOW_HEIGHT,
    AVAILABLE_MODELS, DEFAULT_MODEL, LANGUAGE_OPTIONS, DEFAULT_LANGUAGE,
    SUPPORTED_AUDIO_FORMATS,
)
from utils import detect_device
from recognizer import WhisperRecognizer
from separator import separate_vocals, is_demucs_available
from lrc_writer import save_lrc, save_empty_lrc


class App:
    """主应用类：管理 GUI 和后台任务调度"""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{APP_TITLE} v2.0")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.resizable(True, True)

        # ── 状态变量 ──────────────────────────────────────
        self.audio_path = tk.StringVar()
        self.model_var = tk.StringVar(value=DEFAULT_MODEL)
        self.lang_var = tk.StringVar(value=DEFAULT_LANGUAGE)
        self.separate_var = tk.BooleanVar(value=True)
        self.simplified_var = tk.BooleanVar(value=True)
        self.running = False
        self.log_queue: queue.Queue[str] = queue.Queue()

        # ── 模型缓存（复用，避免重复加载）──────────────────
        self._recognizer: WhisperRecognizer | None = None
        self._current_model_size: str | None = None

        # ── 设备信息 ──────────────────────────────────────
        self.device, self.device_name = detect_device()

        self._setup_ui()
        self.root.after(500, self._check_dependencies)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  UI 构建
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _setup_ui(self):
        # 标题
        tk.Label(
            self.root, text=APP_TITLE,
            font=("Microsoft YaHei", 18, "bold")
        ).pack(pady=10)

        tk.Label(
            self.root, text=APP_SUBTITLE,
            font=("Microsoft YaHei", 10), fg="gray"
        ).pack()

        # ── 文件选择 ──────────────────────────────────────
        frame_file = tk.LabelFrame(self.root, text="📂 选择音频文件", padx=10, pady=10)
        frame_file.pack(fill=tk.X, padx=20, pady=10)

        tk.Entry(frame_file, textvariable=self.audio_path, width=50).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        tk.Button(frame_file, text="浏览", command=self._select_file, width=8).pack(side=tk.RIGHT)

        # ── 设置区域 ──────────────────────────────────────
        frame_settings = tk.LabelFrame(self.root, text="⚙️ 设置", padx=10, pady=10)
        frame_settings.pack(fill=tk.X, padx=20, pady=5)

        # 设备信息
        device_label = f"{self.device} ({self.device_name})" if self.device == "cuda" else "CPU"
        tk.Label(frame_settings, text=f"计算设备: {device_label}",
                 font=("Microsoft YaHei", 9), fg="#2196F3").grid(
            row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 5))

        # 模型选择
        tk.Label(frame_settings, text="识别模型:").grid(row=1, column=0, sticky=tk.W, pady=3)
        ttk.Combobox(
            frame_settings, textvariable=self.model_var,
            values=AVAILABLE_MODELS, state="readonly", width=15
        ).grid(row=1, column=1, sticky=tk.W, padx=10)
        tk.Label(frame_settings, text="(small 推荐，越大越准但越慢)",
                 font=("Microsoft YaHei", 9), fg="gray").grid(row=1, column=2, sticky=tk.W)

        # 语言选择
        tk.Label(frame_settings, text="歌词语言:").grid(row=2, column=0, sticky=tk.W, pady=3)
        lang_combo = ttk.Combobox(
            frame_settings, textvariable=self.lang_var,
            values=list(LANGUAGE_OPTIONS.keys()),
            state="readonly", width=15
        )
        lang_combo.set(DEFAULT_LANGUAGE)
        lang_combo.grid(row=2, column=1, sticky=tk.W, padx=10)

        # 人声分离
        self.separate_check = tk.Checkbutton(
            frame_settings, text="启用人声分离 (推荐 - 大幅提高准确率)",
            variable=self.separate_var)
        self.separate_check.grid(row=3, column=0, columnspan=3, sticky=tk.W, pady=3)

        # 简繁转换
        self.simplified_check = tk.Checkbutton(
            frame_settings, text="输出简体中文 (取消勾选则保留原始输出)",
            variable=self.simplified_var)
        self.simplified_check.grid(row=4, column=0, columnspan=3, sticky=tk.W, pady=2)

        # ── 进度条 ────────────────────────────────────────
        frame_progress = tk.LabelFrame(self.root, text="📊 进度", padx=10, pady=10)
        frame_progress.pack(fill=tk.X, padx=20, pady=5)

        self.progress = ttk.Progressbar(frame_progress, mode='indeterminate')
        self.progress.pack(fill=tk.X, pady=5)

        # ── 日志输出 ──────────────────────────────────────
        frame_log = tk.LabelFrame(self.root, text="📝 日志", padx=10, pady=10)
        frame_log.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

        self.log_text = tk.Text(frame_log, height=10, wrap=tk.WORD,
                                font=("Consolas", 10))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        scroll = tk.Scrollbar(self.log_text)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scroll.set)
        scroll.config(command=self.log_text.yview)

        # ── 按钮区域 ──────────────────────────────────────
        frame_button = tk.Frame(self.root)
        frame_button.pack(pady=10)

        self.start_btn = tk.Button(
            frame_button, text="▶️ 开始识别",
            command=self._start_recognition,
            font=("Microsoft YaHei", 12, "bold"),
            bg="#4CAF50", fg="white", width=15, height=1)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        tk.Button(
            frame_button, text="❌ 退出", command=self.root.quit,
            font=("Microsoft YaHei", 10), width=10
        ).pack(side=tk.LEFT, padx=5)

        # ── 状态栏 ────────────────────────────────────────
        self.status_var = tk.StringVar(value="就绪")
        tk.Label(
            self.root, textvariable=self.status_var,
            bd=1, relief=tk.SUNKEN, anchor=tk.W
        ).pack(side=tk.BOTTOM, fill=tk.X)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  事件处理
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _select_file(self):
        path = filedialog.askopenfilename(
            title="选择音频文件",
            filetypes=SUPPORTED_AUDIO_FORMATS)
        if path:
            self.audio_path.set(path)

    def _check_dependencies(self):
        self._log("正在检查依赖库...")

        try:
            from faster_whisper import WhisperModel
            self._log("✅ faster-whisper 可用")
        except ImportError:
            self._log("❌ 未安装 faster-whisper！请执行: pip install faster-whisper")

        try:
            import librosa
            import soundfile
            self._log("✅ librosa / soundfile 可用")
        except ImportError:
            self._log("❌ 未安装 librosa/soundfile！请执行: pip install librosa soundfile")

        if is_demucs_available():
            self._log("✅ Demucs (人声分离) 可用")
        else:
            self._log("⚠️ demucs 未安装，人声分离功能将不可用。安装: pip install demucs")

        if self.device == "cuda":
            self._log(f"✅ GPU 加速已启用: {self.device_name}")
        else:
            self._log("ℹ️ 当前使用 CPU 模式（速度较慢）")

        self._log("✅ 环境检查完毕\n")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  识别流程
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _start_recognition(self):
        """点击「开始识别」按钮后的入口"""
        if self.running:
            return

        audio_path = self.audio_path.get()
        if not audio_path:
            messagebox.showwarning("提示", "请先选择音频文件")
            return

        if not os.path.isfile(audio_path):
            messagebox.showerror("错误", f"文件不存在:\n{audio_path}")
            return

        try:
            from faster_whisper import WhisperModel
        except ImportError:
            messagebox.showerror("错误", "缺少 faster-whisper 库，无法运行\n"
                                        "请执行: pip install faster-whisper")
            return

        # 解析语言
        lang_key = self.lang_var.get()
        lang = LANGUAGE_OPTIONS.get(lang_key)

        model_size = self.model_var.get()

        self.running = True
        self.start_btn.config(state=tk.DISABLED, text="⏳ 识别中...")
        self.progress.start()
        self.status_var.set("正在运行...")

        # 在后台线程中运行，避免 GUI 卡死
        t = threading.Thread(
            target=self._run_recognition,
            args=(audio_path, model_size, lang,
                  self.separate_var.get(), self.simplified_var.get()),
            daemon=True
        )
        t.start()

        # 开始轮询日志队列
        self._poll_log_queue()

    def _run_recognition(self, audio_path: str, model_size: str,
                         lang: str | None, separate: bool, simplified: bool):
        """后台线程：执行完整的识别流程"""
        try:
            self._enqueue_log(f"🚀 开始处理: {os.path.basename(audio_path)}")

            # ── 1. 人声分离 ───────────────────────────────
            vocal_file = None
            if separate:
                if is_demucs_available():
                    vocal_file = separate_vocals(
                        audio_path, device=self.device, log_callback=self._enqueue_log)
                else:
                    self._enqueue_log("⚠️ demucs 未安装，跳过人声分离")

            target = vocal_file if vocal_file else audio_path

            # ── 2. Whisper 识别（模型缓存复用）────────────
            recognizer = self._get_or_create_recognizer(model_size)
            lyrics = recognizer.transcribe(target, language=lang)

            # ── 3. 简繁转换 ───────────────────────────────
            if lang == 'zh' and simplified:
                lyrics = [(s, e, zhconv.convert(t, 'zh-cn')) for s, e, t in lyrics]
                self._enqueue_log("   🔄 已转换为简体中文")

            # ── 4. 保存 LRC ───────────────────────────────
            if not lyrics:
                self._enqueue_log("\n⚠️ 没有识别到歌词！可能是纯音乐或人声不清晰。")
                save_empty_lrc(audio_path, log_callback=self._enqueue_log)
            else:
                save_lrc(lyrics, audio_path, log_callback=self._enqueue_log)
                self._enqueue_log(f"\n✅ 成功生成 {len(lyrics)} 行歌词")

        except MemoryError:
            self._enqueue_log("❌ 内存不足！请尝试使用更小的模型（如 tiny 或 base）")
        except FileNotFoundError as e:
            self._enqueue_log(f"❌ 文件未找到: {e}")
        except RuntimeError as e:
            if "out of memory" in str(e).lower():
                self._enqueue_log("❌ GPU 显存不足！请尝试使用更小的模型")
            else:
                self._enqueue_log(f"❌ 运行时错误: {e}")
        except Exception as e:
            self._enqueue_log(f"❌ 发生未知错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self._enqueue_log("DONE")

    def _get_or_create_recognizer(self, model_size: str) -> WhisperRecognizer:
        """
        获取或创建 WhisperRecognizer 实例。
        如果模型大小不变，直接复用已有实例；否则重新创建。
        """
        if (self._recognizer is not None
                and self._current_model_size == model_size):
            self._enqueue_log(f"\n🎙️ 复用已加载的 Whisper 模型 ({model_size})")
            return self._recognizer

        # 卸载旧模型
        if self._recognizer is not None:
            self._recognizer.unload_model()

        self._recognizer = WhisperRecognizer(
            model_size=model_size,
            device=self.device,
            log_callback=self._enqueue_log
        )
        self._recognizer.load_model()
        self._current_model_size = model_size
        return self._recognizer

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  日志系统（线程安全：后台 → Queue → GUI）
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _enqueue_log(self, msg: str):
        """后台线程调用：将日志放入队列"""
        self.log_queue.put(msg)

    def _log(self, msg: str):
        """GUI 线程调用：直接写入 Text 控件"""
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)

    def _poll_log_queue(self):
        """GUI 线程轮询队列，将后台日志显示到界面"""
        try:
            while True:
                msg = self.log_queue.get_nowait()
                if msg == "DONE":
                    self.running = False
                    self.start_btn.config(state=tk.NORMAL, text="▶️ 开始识别")
                    self.progress.stop()
                    self.status_var.set("就绪")
                    return
                self._log(msg)
        except queue.Empty:
            pass

        if self.running:
            self.root.after(200, self._poll_log_queue)
