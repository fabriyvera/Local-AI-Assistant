import os
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import httpx
import json
import uuid
from rag import add_document, search_similar
from tts import text_to_speech
from stt import speech_to_text
from fastapi import UploadFile, File
import tempfile
from fastapi.responses import FileResponse

app = FastAPI()

OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "qwen2.5-coder:3b"

SYSTEM_PROMPT = """Eres un asistente experto en desarrollo de software web 
(React, Node.js, FastAPI, Go) y ciencia de datos (Python, pandas, NumPy, 
scikit-learn, análisis estadístico). Respondes con precisión técnica, 
das ejemplos de código cuando es útil, y señalas trade-offs cuando existen 
varias soluciones válidas. Eres conciso pero completo."""

# Historial simple en memoria (se pierde al reiniciar el servidor)
conversation_history: dict[str, list[dict]] = {}

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    model: str = DEFAULT_MODEL
    use_rag: bool = True

class DocumentRequest(BaseModel):
    text: str
    metadata: dict = {}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/documents")
async def upload_document(request: DocumentRequest):
    doc_id = str(uuid.uuid4())
    await add_document(doc_id, request.text, request.metadata)
    return {"id": doc_id, "status": "indexed"}

@app.get("/chat/history/{session_id}")
async def get_history(session_id: str):
    return {"history": conversation_history.get(session_id, [])}

@app.delete("/chat/history/{session_id}")
async def clear_history(session_id: str):
    conversation_history[session_id] = []
    return {"status": "cleared"}

@app.post("/chat")
async def chat(request: ChatRequest):
    history = conversation_history.setdefault(request.session_id, [])

    context_parts = [SYSTEM_PROMPT]

    if request.use_rag:
        relevant_docs = await search_similar(request.message)
        if relevant_docs:
            context_parts.append("\nContexto relevante de tu documentación:")
            context_parts.extend(f"- {doc}" for doc in relevant_docs)

    if history:
        context_parts.append("\nHistorial de conversación:")
        for turn in history[-5:]:  # últimos 5 turnos para no saturar contexto
            context_parts.append(f"Usuario: {turn['user']}")
            context_parts.append(f"Asistente: {turn['assistant']}")

    context_parts.append(f"\nUsuario: {request.message}\nAsistente:")
    full_prompt = "\n".join(context_parts)

    full_response = []

    async def stream_response():
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                OLLAMA_URL,
                json={
                    "model": request.model,
                    "prompt": full_prompt,
                    "stream": True
                }
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        data = json.loads(line)
                        if "response" in data:
                            full_response.append(data["response"])
                            yield data["response"]

        history.append({
            "user": request.message,
            "assistant": "".join(full_response)
        })

    return StreamingResponse(stream_response(), media_type="text/plain")

class SpeakRequest(BaseModel):
    text: str

@app.post("/speak")
async def speak(request: SpeakRequest):
    audio_path = text_to_speech(request.text)
    return FileResponse(audio_path, media_type="audio/wav", filename="response.wav")


@app.post("/chat-voice")
async def chat_voice(request: ChatRequest):
    history = conversation_history.setdefault(request.session_id, [])

    context_parts = [SYSTEM_PROMPT]

    if request.use_rag:
        relevant_docs = await search_similar(request.message)
        if relevant_docs:
            context_parts.append("\nContexto relevante de tu documentación:")
            context_parts.extend(f"- {doc}" for doc in relevant_docs)

    if history:
        context_parts.append("\nHistorial de conversación:")
        for turn in history[-5:]:
            context_parts.append(f"Usuario: {turn['user']}")
            context_parts.append(f"Asistente: {turn['assistant']}")

    context_parts.append(f"\nUsuario: {request.message}\nAsistente:")
    full_prompt = "\n".join(context_parts)

    # Obtener respuesta completa del LLM (sin streaming, la necesitamos entera para TTS)
    async with httpx.AsyncClient(timeout=None) as client:
        response = await client.post(
            OLLAMA_URL,
            json={
                "model": request.model,
                "prompt": full_prompt,
                "stream": False
            }
        )
        llm_text = response.json()["response"]

    history.append({"user": request.message, "assistant": llm_text})

    # Convertir a voz
    audio_path = text_to_speech(llm_text)

    return FileResponse(
        audio_path,
        media_type="audio/wav",
        filename="response.wav",
        headers={"X-Response-Text": llm_text[:500]}  # texto en header, por si el cliente lo necesita
    )


@app.post("/listen")
async def listen(audio: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        content = await audio.read()
        tmp.write(content)
        tmp_path = tmp.name

    text = speech_to_text(tmp_path)
    os.remove(tmp_path)

    return {"text": text}
