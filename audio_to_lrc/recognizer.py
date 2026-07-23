"""
Whisper 语音识别模块
支持模型缓存复用、GPU/CPU 自动切换
"""

from __future__ import annotations

import os
import logging
from typing import TYPE_CHECKING

from config import (
    TARGET_SAMPLE_RATE,
    LRC_MIN_TEXT_LENGTH,
    DEVICE_COMPUTE_MAP,
    WHISPER_PROMPTS,
    DEFAULT_WHISPER_PROMPT,
)
from utils import clean_lyric_text, detect_device

if TYPE_CHECKING:
    from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)


class WhisperRecognizer:
    """
    Whisper 语音识别器。
    模型在实例化时加载一次，后续复用，避免重复加载开销。
    """

    def __init__(self, model_size: str = "small", device: str | None = None,
                 log_callback=None):
        """
        Args:
            model_size: Whisper 模型大小 (tiny/base/small/medium/large-v3)
            device: 计算设备，None 表示自动检测
            log_callback: 日志回调函数
        """
        self.log_callback = log_callback
        self.model_size = model_size

        self.model: "WhisperModel | None" = None

        # 自动检测设备
        if device is None:
            self.device, self.device_name = detect_device()
        else:
            self.device = device
            self.device_name = device

        self.compute_type = DEVICE_COMPUTE_MAP.get(self.device, "float16")

    def _log(self, msg: str):
        if self.log_callback:
            self.log_callback(msg)
        logger.info(msg)

    def load_model(self):
        """加载 Whisper 模型（仅加载一次，后续调用复用）"""
        if self.model is not None:
            return

        from faster_whisper import WhisperModel

        self._log(f"\n🎙️ 加载 Whisper 模型 ({self.model_size})...")
        self._log(f"   设备: {self.device} ({self.device_name})")
        self._log(f"   计算精度: {self.compute_type}")

        self.model = WhisperModel(
            self.model_size,
            device=self.device,
            compute_type=self.compute_type
        )
        self._log("   ✅ 模型就绪")

    def _get_initial_prompt(self, language: str | None) -> str:
        if language:
            lang = language.lower()
            if lang in WHISPER_PROMPTS:
                return WHISPER_PROMPTS[lang]
        return DEFAULT_WHISPER_PROMPT

    def transcribe(self, audio_path: str, language: str | None = None) -> list[tuple[float, float, str]]:
        """转录音频文件并返回歌词列表。"""
        if self.model is None:
            self.load_model()

        assert self.model is not None

        self._log("   开始转录...")
        target_path = audio_path
        temp_wav = None
        if not audio_path.lower().endswith('.wav'):
            target_path, temp_wav = self._convert_to_wav(audio_path)

        try:
            segments, info = self.model.transcribe(
                target_path,
                language=language,
                beam_size=5,
                best_of=5,
                patience=1.0,
                condition_on_previous_text=True,
                initial_prompt=self._get_initial_prompt(language),
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=300, threshold=0.3, speech_pad_ms=200),
                no_speech_threshold=0.4,
                log_prob_threshold=-0.8,
            )

            self._log(f"   📊 检测语言: {info.language} ({info.language_probability:.0%})")
            lyrics = [
                (seg.start, seg.end, text)
                for seg in segments
                if (text := clean_lyric_text(seg.text)) and len(text) >= LRC_MIN_TEXT_LENGTH
            ]
            self._log(f"   📝 有效歌词: {len(lyrics)} 行")
            return lyrics

        except RuntimeError as e:
            if "out of memory" in str(e).lower():
                self._log("   ❌ GPU 显存不足，请尝试使用更小的模型")
            else:
                self._log(f"   ❌ 识别运行时错误: {e}")
            raise
        except Exception as e:
            self._log(f"   ❌ 识别失败: {e}")
            raise
        finally:
            # 清理临时文件
            if temp_wav and os.path.exists(temp_wav):
                try:
                    os.remove(temp_wav)
                except OSError:
                    pass


    def _convert_to_wav(self, audio_path: str) -> tuple[str, str | None]:
        """
        将非 WAV 音频转换为 16kHz 单声道 WAV。

        Returns:
            (target_path, temp_wav_path)
            如果转换失败，返回原始路径和 None
        """
        try:
            import librosa
            import soundfile as sf

            self._log("   🔄 转换为 WAV...")
            audio, sr = librosa.load(audio_path, sr=TARGET_SAMPLE_RATE, mono=True)
            temp_wav = audio_path.rsplit('.', 1)[0] + '_temp.wav'
            sf.write(temp_wav, audio, int(sr))
            return temp_wav, temp_wav

        except ImportError:
            self._log("   ⚠️ librosa/soundfile 未安装，无法转换格式")
            return audio_path, None
        except Exception as e:
            self._log(f"   ⚠️ 音频转换失败: {e}，尝试直接使用原文件")
            return audio_path, None

    def unload_model(self):
        """卸载模型释放显存"""
        if self.model is not None:
            del self.model
            self.model = None
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass
            self._log("   🗑️ 模型已卸载")
