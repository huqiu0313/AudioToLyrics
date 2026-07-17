from faster_whisper import WhisperModel

model = WhisperModel(
    "base",
    device="cuda",
    compute_type="float16"
)

print("模型加载成功")