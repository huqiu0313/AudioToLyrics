"""加密音频解密：通过 unlock-music CLI (um.exe) 解密主流音乐平台的加密音频文件

首次使用时，若 tools/um.exe 不存在，会自动从 Gitee 镜像下载。
"""

import io
import threading
import zipfile
from pathlib import Path
from typing import Callable

import requests

from config import (
    ENCRYPTED_FORMATS,
    UM_CLI_NAME,
    UM_CLI_DOWNLOAD_URL,
    UM_CLI_ZIP_ENTRY,
    UM_DOWNLOAD_TIMEOUT,
    UM_RUN_TIMEOUT,
)
from utils.paths import app_data_dir
from utils.process import run_cancellable


def is_encrypted(file_path: str) -> bool:
    """判断文件是否为加密音频格式"""
    return Path(file_path).suffix.lower() in ENCRYPTED_FORMATS


def _get_um_cli_path() -> Path:
    """返回 um.exe 的预期路径（打包运行时位于 %APPDATA% 数据目录）"""
    return app_data_dir() / "tools" / UM_CLI_NAME


def ensure_um_cli(
    progress_callback: Callable[[int, str], None] | None = None,
) -> Path:
    """
    确保 unlock-music CLI 可用：若不存在则自动下载。

    参数:
        progress_callback: 可选的进度回调 (percent, message)

    返回:
        um.exe 的路径
    """
    cli_path = _get_um_cli_path()
    if cli_path.exists():
        return cli_path

    # 需要下载
    if progress_callback:
        progress_callback(1, "正在下载 unlock-music 解密工具...")

    try:
        resp = requests.get(UM_CLI_DOWNLOAD_URL, timeout=UM_DOWNLOAD_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(
            f"下载 unlock-music CLI 失败: {e}\n"
            f"请手动下载 um-windows-amd64.exe 并放到 tools/ 目录，"
            f"重命名为 {UM_CLI_NAME}\n"
            f"下载地址: https://gitee.com/pnceon/unlock-music/releases"
        ) from e

    if progress_callback:
        progress_callback(4, "正在解压 unlock-music 工具...")

    # 从 zip 中提取 um-windows-amd64.exe
    try:
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            with zf.open(UM_CLI_ZIP_ENTRY) as src:
                cli_path.parent.mkdir(parents=True, exist_ok=True)
                with open(cli_path, "wb") as dst:
                    dst.write(src.read())
    except (KeyError, zipfile.BadZipFile) as e:
        raise RuntimeError(
            f"解压 unlock-music CLI 失败: {e}\n"
            f"请手动下载 um-windows-amd64.exe 并放到 tools/ 目录"
        ) from e

    if progress_callback:
        progress_callback(6, f"unlock-music 工具已就绪: {cli_path.name}")

    return cli_path


def decrypt_audio(
    file_path: str,
    output_dir: str | None = None,
    progress_callback: Callable[[int, str], None] | None = None,
    cancel_event: threading.Event | None = None,
) -> str:
    """
    使用 unlock-music CLI 解密加密音频文件。

    参数:
        file_path: 加密音频文件路径
        output_dir: 解密后文件的输出目录，None 则输出到源文件同目录
        progress_callback: 可选的进度回调
        cancel_event: 可选的取消事件，set 后解密子进程会被终止

    返回:
        解密后的音频文件路径
    """
    um_cli = ensure_um_cli(progress_callback)
    file_path = Path(file_path)

    if output_dir:
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
    else:
        out_dir = file_path.parent

    # 记录解密前输出目录中已有的文件，用于对比找出新生成的文件
    existing_files = set(out_dir.iterdir()) if out_dir.exists() else set()

    # 调用 unlock-music CLI: um.exe -o <output_dir> <input_file>
    cmd = [
        str(um_cli),
        "-o", str(out_dir),
        str(file_path),
    ]

    result = run_cancellable(cmd, timeout=UM_RUN_TIMEOUT, cancel_event=cancel_event)

    if result.returncode != 0:
        raise RuntimeError(
            f"unlock-music 解密失败: {result.stderr[:300] or result.stdout[:300]}"
        )

    # 对比输出目录，找到新生成的文件
    new_files = set(out_dir.iterdir()) - existing_files
    # 过滤掉隐藏文件和临时文件
    new_files = {f for f in new_files if not f.name.startswith(".")}

    if not new_files:
        # 若对比方式未找到，尝试从 um.exe 输出中解析文件路径
        decoded_path = _parse_output_path(result.stdout, out_dir, file_path)
        if decoded_path:
            return str(decoded_path)
        raise FileNotFoundError(
            f"解密完成但未找到输出文件，um.exe 输出: {result.stdout[:300]}"
        )

    # 返回最新生成的文件（通常只有一个）
    decoded_file = sorted(new_files, key=lambda f: f.stat().st_mtime, reverse=True)[0]
    return str(decoded_file)


def _parse_output_path(
    stdout: str, out_dir: Path, source: Path
) -> Path | None:
    """
    尝试从 um.exe 的标准输出中解析解密后文件的路径。
    um.exe 通常会输出类似 "解密成功: xxx.mp3" 的信息。
    """
    for line in stdout.splitlines():
        line = line.strip()
        # 尝试匹配输出目录中同名但不同后缀的文件
        if out_dir.name in line or source.stem in line:
            # 提取可能的文件路径
            for part in line.split():
                candidate = out_dir / part
                if candidate.exists() and candidate.suffix.lower() not in ENCRYPTED_FORMATS:
                    return candidate
    # 兜底：查找输出目录中与源文件同名的非加密文件
    for f in out_dir.iterdir():
        if f.stem == source.stem and f.suffix.lower() not in ENCRYPTED_FORMATS:
            return f
    return None
