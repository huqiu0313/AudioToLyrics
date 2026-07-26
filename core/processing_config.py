"""处理配置：GUI 字典配置 → 强类型 ProcessingConfig 的唯一入口"""

from dataclasses import dataclass

from config import (
    DEFAULT_DEMUCS_MODEL,
    DEFAULT_WHISPER_MODEL,
    LYRICS_PROVIDERS,
)
from utils.logging_setup import get_logger

logger = get_logger(__name__)

# 各字段期望类型（from_dict 宽容解析时校验，不符则落回默认值）
_FIELD_TYPES: dict[str, type | tuple[type, ...]] = {
    "whisper_model": str,
    "demucs_model": str,
    "providers": (list, tuple, type(None)),
    "auto_convert_video": bool,
    "use_demucs": bool,
    "use_whisper": bool,
    "decrypt_output_dir": (str, type(None)),
    "delete_source_after_convert": bool,
}


@dataclass(frozen=True)
class ProcessingConfig:
    """单文件处理流程的全部可调参数（默认值唯一来源 = config.py）"""

    whisper_model: str = DEFAULT_WHISPER_MODEL
    demucs_model: str = DEFAULT_DEMUCS_MODEL
    providers: tuple[str, ...] | None = None  # None = 按 LYRICS_PROVIDERS 全部启用
    auto_convert_video: bool = True
    use_demucs: bool = False
    use_whisper: bool = False
    decrypt_output_dir: str | None = None
    delete_source_after_convert: bool = False

    @classmethod
    def from_dict(cls, d: dict | None) -> "ProcessingConfig":
        """
        宽容解析 GUI 传入的 dict：
        - None/空 dict → 全默认值
        - 未知 key → warning 日志后忽略
        - 类型不符 → 该字段落回默认值并 warning
        - providers: list→tuple；空列表→None；非法平台名过滤并 warning
        """
        if not d:
            return cls()

        fields = cls.__dataclass_fields__
        unknown = set(d) - set(fields)
        if unknown:
            logger.warning("配置中存在未知键，已忽略: %s", sorted(unknown))

        kwargs = {}
        for key, value in d.items():
            if key not in fields:
                continue
            expected = _FIELD_TYPES[key]
            if not isinstance(value, expected):
                logger.warning(
                    "配置项 %s 类型不符（期望 %s，实际 %s），使用默认值",
                    key, expected, type(value).__name__,
                )
                continue
            if key == "providers":
                value = cls._parse_providers(value)
            elif key == "decrypt_output_dir" and value == "":
                value = None  # 空字符串等价于未设置
            kwargs[key] = value
        return cls(**kwargs)

    @staticmethod
    def _parse_providers(value) -> tuple[str, ...] | None:
        if not value:
            return None
        valid = [p for p in value if p in LYRICS_PROVIDERS]
        invalid = set(value) - set(LYRICS_PROVIDERS)
        if invalid:
            logger.warning("忽略未知歌词平台: %s", sorted(invalid))
        return tuple(valid) or None
