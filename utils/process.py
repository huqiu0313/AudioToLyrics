"""可取消的子进程执行：Popen + 轮询，支持 threading.Event 取消"""

import subprocess
import tempfile
import threading
import time

_POLL_INTERVAL = 0.2    # 取消/超时轮询间隔（秒）
_TERMINATE_GRACE = 3.0  # terminate 后到 kill 的宽限（秒）


class ProcessCancelledError(Exception):
    """子进程因取消请求被终止"""


def run_cancellable(
    cmd: list[str],
    timeout: float,
    cancel_event: threading.Event | None = None,
) -> subprocess.CompletedProcess:
    """
    与 subprocess.run(capture_output=True, text=True, timeout=...) 语义一致，
    但运行期间可通过 cancel_event 请求取消：

    - cancel_event.set() → terminate() → 3 秒宽限 → kill()，
      然后抛出 ProcessCancelledError
    - 超时 → kill() 后抛出 subprocess.TimeoutExpired（与 subprocess.run 一致）

    实现说明：输出重定向到临时文件而非管道。管道方案在输出超过缓冲区
    （Windows 64KB）时会因子进程阻塞写入而死锁（poll 轮询不读管道），
    且 ffmpeg/demucs 输出中的非 GBK 字节会让 text=True 的读取线程崩溃。
    """
    with tempfile.TemporaryFile() as out_f, tempfile.TemporaryFile() as err_f:
        proc = subprocess.Popen(cmd, stdout=out_f, stderr=err_f)
        try:
            deadline = time.monotonic() + timeout
            while proc.poll() is None:
                if cancel_event is not None and cancel_event.is_set():
                    _terminate_then_kill(proc)
                    raise ProcessCancelledError("操作已取消")
                if time.monotonic() > deadline:
                    proc.kill()
                    proc.wait()
                    raise subprocess.TimeoutExpired(cmd, timeout)
                time.sleep(_POLL_INTERVAL)
        except BaseException:
            # 兜底：任何异常路径都不留下仍在运行的子进程
            if proc.poll() is None:
                proc.kill()
                proc.wait()
            raise

        out_f.seek(0)
        err_f.seek(0)
        stdout = out_f.read().decode("utf-8", errors="replace")
        stderr = err_f.read().decode("utf-8", errors="replace")

    return subprocess.CompletedProcess(cmd, proc.returncode, stdout, stderr)


def _terminate_then_kill(proc: subprocess.Popen) -> None:
    """先温和终止，宽限期满后强杀"""
    proc.terminate()
    try:
        proc.wait(timeout=_TERMINATE_GRACE)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
