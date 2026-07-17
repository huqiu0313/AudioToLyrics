"""Whisper 语音识别：将音频转换为带时间戳的文本段落"""

from faster_whisper import WhisperModel

# 模块级模型缓存，避免重复加载
_model: WhisperModel | None = None
_model_name: str | None = None


def _get_model(model_name: str) -> WhisperModel:
    """获取或缓存 WhisperModel 实例"""
    global _model, _model_name
    if _model is not None and _model_name == model_name:
        return _model

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
    model_name: str = "base",
) -> list[dict]:
    """
    使用 faster-whisper 对音频进行语音识别。

    自动检测语言，返回带时间戳的段落列表。

    参数:
        audio_path: 音频文件路径（建议为分离后的人声 wav）
        model_name: Whisper 模型名（tiny / base / small / medium / large-v3）

    返回:
        [{start: float, end: float, text: str}, ...]
        start/end 单位为秒
    """
    model = _get_model(model_name)

    segments, info = model.transcribe(
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


def get_detected_language(audio_path: str, model_name: str = "base") -> str:
    """检测音频的语言代码（如 'zh', 'en', 'ja'）"""
    model = _get_model(model_name)
    segments, info = model.transcribe(audio_path, language=None, beam_size=1)
    # 消费生成器以获取 info
    for _ in segments:
        pass
    return info.language
