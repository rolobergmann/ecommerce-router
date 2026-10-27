"""API FastAPI que expone el agente router del ecommerce.

Levantar en local:
    uvicorn api.app:app --reload --port 8000

Documentación interactiva (Swagger) en http://localhost:8000/docs
"""

import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# El grafo se importa (y por tanto se compila con MemorySaver) UNA sola vez,
# al arrancar la app; no en cada request.
from src.router.graph import graph

load_dotenv()

logger = logging.getLogger("api.router")

MODELO = os.getenv("MODELO", "")

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


@app.post("/telegram", tags=["telegram"], include_in_schema=False)
async def telegram(update: dict) -> dict:
    # Por ahora acepta cualquier JSON y responde ok. Se completa en la parte 5.
    return {"ok": True}
