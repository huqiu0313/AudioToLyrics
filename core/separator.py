"""Demucs 人声分离：从混合音频中提取人声轨道（通过子进程调用，避免 CUDA 上下文冲突）"""

import sys
import subprocess
import tempfile
from pathlib import Path


def separate_vocals(
    audio_path: str,
    model_name: str = "htdemucs",
    device: str | None = None,
    output_dir: str | None = None,
) -> str:
    """
    使用 Demucs 从音频中分离人声（通过子进程运行，确保 GPU 资源完全释放）。

    参数:
        audio_path: 输入音频文件路径
        model_name: Demucs 模型名（htdemucs / htdemucs_ft）
        device: 运算设备（"cuda" / "cpu"），None 则自动检测
        output_dir: 输出目录，None 则使用临时目录

    返回:
        分离后的人声 wav 文件路径
    """
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

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"Demucs 分离失败: {result.stderr[:300]}")

    # Demucs 输出路径: output_dir/model_name/stem_name/vocals.wav
    stem_name = Path(audio_path).stem
    vocal_path = Path(output_dir) / model_name / stem_name / "vocals.wav"

    if not vocal_path.exists():
        raise FileNotFoundError(f"Demucs 输出文件未找到: {vocal_path}")

    return str(vocal_path)
