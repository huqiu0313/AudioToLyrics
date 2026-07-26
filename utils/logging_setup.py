"""日志系统初始化：控制台 + 滚动文件双通道（全项目统一入口）"""

import logging
import sys
from logging.handlers import RotatingFileHandler

from utils.paths import app_data_dir

# 项目 logger 统一前缀，避免与 demucs/torch 等第三方 logger 混淆
LOGGER_NAME = "audiotolyrics"


def get_logger(module_name: str) -> logging.Logger:
    """各模块获取 logger 的统一方式：get_logger(__name__)"""
    return logging.getLogger(f"{LOGGER_NAME}.{module_name}")


def setup_logging(level: int = logging.INFO) -> None:
    """
    初始化项目日志系统（幂等，重复调用不会重复添加 handler）。

    - 控制台（stderr）：INFO 及以上，Windows GBK 控制台安全（errors="replace"）
    - 文件 logs/audiotolyrics.log：DEBUG 及以上，1MB × 3 滚动，UTF-8
    - 日志文件被占用或无权限时降级为仅控制台，不抛错
    """
    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:
        return
    logger.setLevel(logging.DEBUG)  # 级别过滤交给各 handler
    logger.propagate = False

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # 控制台 handler：打包的窗口模式下 sys.stderr 为 None，跳过
    if sys.stderr is not None:
        console = logging.StreamHandler(sys.stderr)
        console.setLevel(level)
        console.setFormatter(fmt)
        # GBK 控制台遇到不可编码字符时替换而非崩溃
        if hasattr(console.stream, "reconfigure"):
            try:
                console.stream.reconfigure(errors="replace")
            except Exception:
                pass
        logger.addHandler(console)

    try:
        log_dir = app_data_dir() / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_dir / "audiotolyrics.log",
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)
    except OSError as e:
        logger.warning("日志文件初始化失败，仅输出到控制台: %s", e)
