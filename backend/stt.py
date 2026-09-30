from faster_whisper import WhisperModel

# "small" es buen balance velocidad/precisión para CPU. 
# Si tu laptop es potente en CPU, puedes probar "medium" para más precisión.
model = WhisperModel("small", device="cpu", compute_type="int8")

def speech_to_text(audio_path: str) -> str:
    segments, info = model.transcribe(audio_path, language="es")
    text = " ".join(segment.text for segment in segments)
    return text.strip()
