"""Whisper 语音识别：将音频转换为带时间戳的文本段落"""

import gc
import threading

from config import DEFAULT_WHISPER_MODEL

# 模块级模型缓存（带锁），避免重复加载；faster_whisper 延迟到首次使用时导入
_lock = threading.Lock()
_model = None  # WhisperModel 实例（延迟加载，类型仅运行时可得）
_model_name: str | None = None


def _release_model_locked() -> None:
    """释放缓存的模型（调用方须已持有 _lock），回收内存与 GPU 显存"""
    global _model, _model_name
    if _model is None:
        return
    _model = None
    _model_name = None
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except ImportError:
        pass


def _get_model(model_name: str):
    """获取或缓存 WhisperModel 实例（线程安全；切换模型时先释放旧模型）"""
    global _model, _model_name
    with _lock:
        if _model is not None and _model_name == model_name:
            return _model

        # 切换模型前释放旧模型，避免 GPU 显存泄漏
        _release_model_locked()

        from faster_whisper import WhisperModel

        # 自动检测设备
        try:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            compute_type = "float16" if device == "cuda" else "int8"
        except ImportError:
            device = "cpu"
            compute_type = "int8"

        _model = WhisperModel(model_name, device=device, compute_type=compute_type)
        _model_name = model_name
        return _model


def transcribe(
    audio_path: str,
    model_name: str = DEFAULT_WHISPER_MODEL,
) -> list[dict]:
    """
    使用 faster-whisper 对音频进行语音识别。

    自动检测语言，返回带时间戳的段落列表。

    参数:
        audio_path: 音频文件路径（建议为分离后的人声 wav）
        model_name: Whisper 模型名（见 config.WHISPER_MODELS）

    返回:
        [{start: float, end: float, text: str}, ...]
        start/end 单位为秒
    """
    model = _get_model(model_name)

    segments, _info = model.transcribe(
        audio_path,
        language=None,          # 自动语言检测
        word_timestamps=True,   # 获取词级时间戳
        beam_size=5,
        vad_filter=True,
        vad_parameters=dict(
            min_silence_duration_ms=300,
            threshold=0.3,
            speech_pad_ms=200,
        ),
    )

    result = []
    for seg in segments:
        text = seg.text.strip()
        if not text:
            continue
        result.append({
            "start": seg.start,
            "end": seg.end,
            "text": text,
        })

    return result
