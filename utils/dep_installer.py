"""依赖按需安装：检查 Python 包是否可用，缺失时自动 pip install"""

import sys
import importlib
import subprocess
from typing import Callable


# 包名 → import 名 映射（pip 包名与 import 名不一致的情况）
_IMPORT_NAMES = {
    "faster-whisper": "faster_whisper",
    "imageio-ffmpeg": "imageio_ffmpeg",
}


def is_available(pip_name: str) -> bool:
    """检查指定 pip 包是否已安装（可 import）"""
    import_name = _IMPORT_NAMES.get(pip_name, pip_name)
    try:
        importlib.import_module(import_name)
        return True
    except ImportError:
        return False


def check_and_install(
    packages: list[str],
    progress_callback: Callable[[int, str], None] | None = None,
) -> bool:
    """
    检查并自动安装缺失的 Python 包。

    参数:
        packages: pip 包名列表（如 ["demucs", "faster-whisper"]）
        progress_callback: 可选的进度回调 (percent, message)

    返回:
        True 表示所有包均已可用，False 表示有安装失败
    """
    missing = [p for p in packages if not is_available(p)]
    if not missing:
        return True

    total = len(missing)
    for i, pkg in enumerate(missing):
        if progress_callback:
            progress_callback(
                int(i / total * 100),
                f"正在安装 {pkg}（{i + 1}/{total}）..."
            )
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", pkg],
                capture_output=True,
                text=True,
                timeout=600,
            )
            if result.returncode != 0:
                if progress_callback:
                    progress_callback(
                        100,
                        f"安装 {pkg} 失败: {result.stderr[:200]}"
                    )
                return False
        except Exception as e:
            if progress_callback:
                progress_callback(100, f"安装 {pkg} 异常: {e}")
            return False

    # 验证安装结果
    still_missing = [p for p in missing if not is_available(p)]
    if still_missing:
        if progress_callback:
            progress_callback(100, f"以下包安装后仍不可用: {', '.join(still_missing)}")
        return False

    if progress_callback:
        progress_callback(100, f"依赖安装完成: {', '.join(missing)}")
    return True
