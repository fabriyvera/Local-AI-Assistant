import subprocess
import uuid
import os

VOICE_MODEL = "./voices/es_MX-claude-high.onnx"
OUTPUT_DIR = "./audio_output"

os.makedirs(OUTPUT_DIR, exist_ok=True)

def text_to_speech(text: str) -> str:
    filename = f"{uuid.uuid4()}.wav"
    output_path = os.path.join(OUTPUT_DIR, filename)

    process = subprocess.run(
        ["piper", "--model", VOICE_MODEL, "--output_file", output_path],
        input=text,
        text=True,
        capture_output=True
    )

    if process.returncode != 0:
        raise RuntimeError(f"Piper error: {process.stderr}")

    return output_path
