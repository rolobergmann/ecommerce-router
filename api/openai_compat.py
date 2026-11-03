"""Capa compatible con OpenAI para exponer el agente router como si fuera un "modelo".

Open WebUI (y cualquier cliente que hable el formato OpenAI) necesita estos dos endpoints:
    GET  /v1/models              -> lista de modelos disponibles
    POST /v1/chat/completions    -> conversación (con o sin streaming)

Por dentro, cada mensaje pasa por el grafo router -> Gemini -> respuesta.
Este archivo es aditivo: no toca /chat ni /telegram. Se monta desde api/app.py.
"""

import json
import logging
import time
import uuid

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.router.graph import graph

logger = logging.getLogger("api.openai_compat")

router = APIRouter(prefix="/v1", tags=["openai"])

MODEL_ID = "ecommerce-router"


class Mensaje(BaseModel):
    role: str
    content: str = ""


class ChatCompletionRequest(BaseModel):
    model: str = MODEL_ID
    messages: list[Mensaje] = []
    stream: bool = False


@router.get("/models")
def listar_modelos() -> dict:
    return {
        "object": "list",
        "data": [{"id": MODEL_ID, "object": "model", "created": int(time.time()), "owned_by": "curso"}],
    }


def _responder(texto: str) -> str:
    """Pasa el mensaje por el router y devuelve la respuesta del agente + la ruta elegida."""
    thread_id = uuid.uuid4().hex  # Open WebUI reenvía el historial, así que cada turno es independiente.
    try:
        final = graph.invoke({"mensaje": texto}, {"configurable": {"thread_id": thread_id}})
        return f"{final['respuesta']}\n\n_(ruta: {final['ruta']} — {final['motivo']})_"
    except Exception:
        logger.exception("El grafo router falló en el endpoint OpenAI")
        return "Ahora mismo no puedo responder. Intenta de nuevo en un momento."


def _ultimo_mensaje_usuario(messages: list[Mensaje]) -> str:
    for m in reversed(messages):
        if m.role == "user" and m.content.strip():
            return m.content
    return ""


@router.post("/chat/completions")
def chat_completions(req: ChatCompletionRequest):
    texto = _ultimo_mensaje_usuario(req.messages)
    contenido = _responder(texto) if texto else "No recibí ningún mensaje."

    cid = f"chatcmpl-{uuid.uuid4().hex}"
    creado = int(time.time())

    if not req.stream:
        return {
            "id": cid,
            "object": "chat.completion",
            "created": creado,
            "model": MODEL_ID,
            "choices": [
                {"index": 0, "message": {"role": "assistant", "content": contenido}, "finish_reason": "stop"}
            ],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }

    # Streaming: enviamos el contenido en un chunk y luego el cierre, en formato SSE de OpenAI.
    def stream():
        base = {"id": cid, "object": "chat.completion.chunk", "created": creado, "model": MODEL_ID}
        primero = {**base, "choices": [{"index": 0, "delta": {"role": "assistant", "content": contenido}, "finish_reason": None}]}
        yield f"data: {json.dumps(primero, ensure_ascii=False)}\n\n"
        cierre = {**base, "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}
        yield f"data: {json.dumps(cierre, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")
