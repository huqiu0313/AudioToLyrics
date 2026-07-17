"""
人声分离模块
优先使用 Demucs Python API，失败时 fallback 到 subprocess
"""

import os
import sys
import subprocess
import logging

from config import DEMUCS_TIMEOUT, DEMUCS_MODEL

logger = logging.getLogger(__name__)


def is_demucs_available() -> bool:
    """检查 demucs 是否已安装（通过 subprocess 探测）"""
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'demucs', '--help'],
            capture_output=True, timeout=10
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def _separate_via_api(audio_path: str, output_dir: str, device: str) -> str | None:
    """通过 Demucs Python API 分离人声（更高效，无需启动子进程）"""
    try:
        from pathlib import Path
        from demucs.api import Separator

        separator = Separator(DEMUCS_MODEL, device=device if device == "cuda" else "cpu")

        wav, sources = separator.separate_audio_file(Path(audio_path))
        vocals = sources["vocals"]

        song_name = os.path.splitext(os.path.basename(audio_path))[0]
        vocal_dir = os.path.join(output_dir, DEMUCS_MODEL, song_name)
        os.makedirs(vocal_dir, exist_ok=True)
        vocal_path = os.path.join(vocal_dir, "vocals.wav")

        import torchaudio
        torchaudio.save(vocal_path, vocals, separator.samplerate)

        logger.info("人声分离完成 (API 模式)")
        return vocal_path

    except ImportError:
        logger.warning("Demucs API 不可用，尝试 subprocess 模式")
        return None
    except Exception as e:
        logger.warning(f"Demucs API 分离失败: {e}，尝试 subprocess 模式")
        return None


def _separate_via_subprocess(audio_path: str, output_dir: str) -> str | None:
    """通过 subprocess 调用 demucs CLI 分离人声（兼容性更好）"""
    song_name = os.path.splitext(os.path.basename(audio_path))[0]

    cmd = [
        sys.executable, '-m', 'demucs',
        '--two-stems', 'vocals',
        '-o', output_dir,
        audio_path
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=DEMUCS_TIMEOUT
        )
        if result.returncode != 0:
            logger.error(f"Demucs 返回错误码 {result.returncode}: {result.stderr[:200]}")
            return None

        vocal_path = os.path.join(output_dir, DEMUCS_MODEL, song_name, "vocals.wav")
        if os.path.exists(vocal_path):
            logger.info("人声分离完成 (subprocess 模式)")
            return vocal_path
        else:
            logger.error(f"人声文件未找到: {vocal_path}")
            return None

    except subprocess.TimeoutExpired:
        logger.error(f"Demucs 超时 ({DEMUCS_TIMEOUT}s)")
        return None
    except FileNotFoundError:
        logger.error("找不到 demucs 可执行文件")
        return None
    except OSError as e:
        logger.error(f"Demucs 执行出错: {e}")
        return None


def separate_vocals(audio_path: str, output_dir: str | None = None,
                    device: str = "cpu",
                    log_callback=None) -> str | None:
    """
    分离人声的主入口。
    优先尝试 Python API，失败则 fallback 到 subprocess。

    Args:
        audio_path: 音频文件路径
        output_dir: 输出目录，默认为音频文件所在目录
        device: 计算设备 ("cuda" 或 "cpu")
        log_callback: 日志回调函数，签名 (msg: str)

    Returns:
        分离后的人声文件路径，失败返回 None
    """
    if output_dir is None:
        output_dir = os.path.dirname(os.path.abspath(audio_path)) or '.'

    def _log(msg: str):
        if log_callback:
            log_callback(msg)
        logger.info(msg)

    _log("🎤 正在分离人声 (Demucs)...")
    _log("   首次运行需下载模型约 800MB，请耐心等待")

    # 优先 API
    vocal_path = _separate_via_api(audio_path, output_dir, device)
    if vocal_path:
        _log("   ✅ 人声分离完成")
        return vocal_path

    # Fallback subprocess
    _log("   ⏳ 切换到 subprocess 模式...")
    vocal_path = _separate_via_subprocess(audio_path, output_dir)
    if vocal_path:
        _log("   ✅ 人声分离完成")
        return vocal_path

    _log("   ⚠️ 人声分离失败，将使用原始音频")
    return None