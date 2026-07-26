"""Demucs 人声分离：从混合音频中提取人声轨道（通过子进程调用，避免 CUDA 上下文冲突）"""

import importlib.util
import sys
import tempfile
import threading
from pathlib import Path

from config import DEFAULT_DEMUCS_MODEL, SUBPROCESS_TIMEOUT
from utils.process import run_cancellable


def separate_vocals(
    audio_path: str,
    model_name: str = DEFAULT_DEMUCS_MODEL,
    device: str | None = None,
    output_dir: str | None = None,
    cancel_event: threading.Event | None = None,
) -> str:
    """
    使用 Demucs 从音频中分离人声（通过子进程运行，确保 GPU 资源完全释放）。

    参数:
        audio_path: 输入音频文件路径
        model_name: Demucs 模型名（htdemucs / htdemucs_ft）
        device: 运算设备（"cuda" / "cpu"），None 则自动检测
        output_dir: 输出目录，None 则使用临时目录
        cancel_event: 可选的取消事件，set 后分离子进程会被终止

    返回:
        分离后的人声 wav 文件路径
    """
    if importlib.util.find_spec("demucs") is None:
        raise RuntimeError(
            "未安装 demucs（安装版不含 AI 组件；"
            "源码版请 pip install -r requirements-ai.txt）"
        )

    if device is None:
        try:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            device = "cpu"

    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="demucs_")

    # 通过子进程运行 Demucs，进程结束后 CUDA 上下文彻底销毁
    # 避免与后续 faster-whisper (CTranslate2) 的 CUDA 上下文冲突
    cmd = [
        sys.executable, "-m", "demucs",
        "--two-stems", "vocals",
        "-n", model_name,
        "-d", device,
        "-o", output_dir,
        audio_path,
    ]

    result = run_cancellable(cmd, timeout=SUBPROCESS_TIMEOUT, cancel_event=cancel_event)
    if result.returncode != 0:
        raise RuntimeError(f"Demucs 分离失败: {result.stderr[:300]}")

    # Demucs 输出路径: output_dir/model_name/stem_name/vocals.wav
    stem_name = Path(audio_path).stem
    vocal_path = Path(output_dir) / model_name / stem_name / "vocals.wav"

    if not vocal_path.exists():
        raise FileNotFoundError(f"Demucs 输出文件未找到: {vocal_path}")

    return str(vocal_path)
