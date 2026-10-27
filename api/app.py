"""API FastAPI que expone el agente router del ecommerce.

Levantar en local:
    uvicorn api.app:app --reload --port 8000

Documentación interactiva (Swagger) en http://localhost:8000/docs
"""

import logging
import os

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

# El grafo se importa (y por tanto se compila con MemorySaver) UNA sola vez,
# al arrancar la app; no en cada request.
from src.router.graph import graph

load_dotenv()

logger = logging.getLogger("api.router")

MODELO = os.getenv("MODELO", "")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_SECRET = os.getenv("TELEGRAM_SECRET", "")
TELEGRAM_API = "https://api.telegram.org"

# --- Metadatos del Swagger (OpenAPI) ------------------------------------------

DESCRIPCION = """\
API del **router** de atención de un ecommerce.

Un nodo clasifica cada mensaje del cliente y lo deriva a uno de tres destinos:

- **preventa**: intención de compra, productos, precios, tallas, stock, pagos antes de comprar.
- **postventa**: pedidos ya hechos, devoluciones, cambios, garantía, producto dañado.
- **generica**: lo que no tiene que ver con la tienda, o saludos sin pedido.
"""

TAGS = [
    {"name": "salud", "description": "Estado de la API."},
    {"name": "chat", "description": "Enrutar un mensaje del cliente."},
    {"name": "telegram", "description": "Webhook de Telegram (se completa en la parte 5)."},
]

app = FastAPI(
    title="Ecommerce Router API",
    version="0.1.0",
    description=DESCRIPCION,
    openapi_tags=TAGS,
)


# --- Modelos de entrada / salida ----------------------------------------------

class ChatRequest(BaseModel):
    user_id: str = Field(
        description="Identificador del cliente. Se usa como thread_id para la memoria de la conversación.",
        examples=["cliente-123"],
    )
    texto: str = Field(
        min_length=1,
        description="Mensaje del cliente a enrutar.",
        examples=["¿tienen la polera azul en talla M?"],
    )


class ChatResponse(BaseModel):
    ruta: str = Field(
        description="Agente elegido: preventa, postventa o generica.",
        examples=["preventa"],
    )
    motivo: str = Field(
        description="Una frase del router explicando por qué eligió esa ruta.",
        examples=["El cliente pregunta por la talla de un producto antes de comprar."],
    )
    respuesta: str = Field(
        description="Respuesta del agente destino.",
        examples=["Soy el agente de preventa. Recibí: ¿tienen la polera azul en talla M? ..."],
    )


class HealthResponse(BaseModel):
    ok: bool = Field(examples=[True])
    modelo: str = Field(description="Modelo configurado en la variable de entorno MODELO.", examples=[MODELO or "gemini-3.5-flash-lite"])


# --- Rutas --------------------------------------------------------------------

@app.get("/health", tags=["salud"], response_model=HealthResponse, summary="Estado de la API")
def health() -> HealthResponse:
    return HealthResponse(ok=True, modelo=MODELO)


@app.post(
    "/chat",
    tags=["chat"],
    response_model=ChatResponse,
    summary="Enrutar un mensaje del cliente",
    responses={
        200: {"description": "El mensaje se enrutó correctamente."},
        422: {"description": "Body inválido (por ejemplo, falta 'texto' o viene vacío)."},
        502: {"description": "El modelo falló al clasificar el mensaje."},
    },
)
def chat(req: ChatRequest) -> ChatResponse:
    config = {"configurable": {"thread_id": req.user_id}}
    try:
        final = graph.invoke({"mensaje": req.texto}, config)
    except Exception:
        # El detalle (y el stack trace) queda en el log del servidor; el cliente
        # solo ve un mensaje genérico, nunca la clave ni la traza.
        logger.exception("El grafo router falló al procesar el mensaje")
        raise HTTPException(status_code=502, detail="El router no está disponible en este momento. Intenta de nuevo.")

    return ChatResponse(ruta=final["ruta"], motivo=final["motivo"], respuesta=final["respuesta"])


def _enviar_telegram(chat_id: int, text: str) -> None:
    """Envía un mensaje al chat con la API de Telegram (sin librerías de bot, solo httpx)."""
    url = f"{TELEGRAM_API}/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        httpx.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)
    except Exception:
        logger.exception("No se pudo enviar el mensaje a Telegram")


@app.post("/telegram", tags=["telegram"], include_in_schema=False)
def telegram(update: dict, x_telegram_bot_api_secret_token: str | None = Header(default=None)) -> dict:
    # Telegram manda este header con el secret_token que registramos en setWebhook.
    if x_telegram_bot_api_secret_token != TELEGRAM_SECRET:
        raise HTTPException(status_code=403, detail="Secret token inválido")

    message = update.get("message") or {}
    text = message.get("text")
    chat_id = (message.get("chat") or {}).get("id")

    # Ignora updates sin texto (fotos, audios, stickers, etc.) o sin chat.
    if not text or chat_id is None:
        return {"ok": True}

    config = {"configurable": {"thread_id": str(chat_id)}}
    try:
        respuesta = graph.invoke({"mensaje": text}, config)["respuesta"]
    except Exception:
        logger.exception("El grafo router falló procesando un mensaje de Telegram")
        respuesta = "Ahora mismo no puedo responder. Intenta de nuevo en un momento."

    _enviar_telegram(chat_id, respuesta)
    # A Telegram siempre le respondemos 200 para que no reintente el update.
    return {"ok": True}
