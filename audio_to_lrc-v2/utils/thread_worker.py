"""后台线程工作器：批量处理文件，支持取消和进度回调"""

import threading
from typing import Callable


class BatchWorker:
    """
    在后台线程中逐文件执行处理任务。

    回调函数 signature:
        progress_callback(file_index, total, percent, message, status)
        - file_index: 当前文件序号（从 1 开始）
        - total: 文件总数
        - percent: 当前文件进度（0-100）
        - message: 状态文本
        - status: "processing" | "done" | "failed" | "cancelled" | "all_done"
    """

    def __init__(
        self,
        file_list: list[str],
        process_func: Callable[[str, Callable], str],
        progress_callback: Callable | None = None,
        config: dict | None = None,
    ):
        self.file_list = list(file_list)
        self.process_func = process_func
        self.progress_callback = progress_callback
        self.config = config or {}

        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._current_file: str = ""

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        """启动后台处理线程"""
        if self.is_running:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """请求停止处理"""
        self._stop_event.set()

    def _run_loop(self) -> None:
        total = len(self.file_list)
        success_count = 0
        fail_count = 0

        for i, audio_path in enumerate(self.file_list):
            if self._stop_event.is_set():
                self._emit(i + 1, total, 0, "已取消", "cancelled")
                break

            self._current_file = audio_path
            self._emit(i + 1, total, 0, f"正在处理: {audio_path}", "processing")

            def _progress(percent: int, message: str) -> None:
                self._emit(i + 1, total, percent, message, "processing")

            try:
                result = self.process_func(audio_path, _progress, self.config)
                self._emit(i + 1, total, 100, result or "完成", "done")
                success_count += 1
            except Exception as e:
                self._emit(i + 1, total, 100, f"失败: {e}", "failed")
                fail_count += 1

        if not self._stop_event.is_set():
            summary = f"全部完成 - 成功: {success_count}, 失败: {fail_count}, 总计: {total}"
            self._emit(total, total, 100, summary, "all_done")

    def _emit(self, file_index: int, total: int, percent: int, message: str, status: str) -> None:
        if self.progress_callback:
            try:
                self.progress_callback(file_index, total, percent, message, status)
            except Exception:
                pass
