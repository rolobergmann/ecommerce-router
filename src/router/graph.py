"""Grafo del agente router: clasifica el mensaje y lo deriva a preventa, postventa o genérica."""

import logging
import os
import warnings
from pathlib import Path
from typing import Annotated, Literal, TypedDict

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from src.router import prompts, tools

load_dotenv()

logger = logging.getLogger("router.graph")

# Algunos modelos (p. ej. gemini-3.5-flash-lite) ignoran temperature y lo avisan en cada llamada.
warnings.filterwarnings("ignore", message=".*uses fixed sampling defaults.*")


class Decision(BaseModel):
    ruta: Literal["preventa", "postventa", "generica"] = Field(description="A qué agente va el mensaje.")
    motivo: str = Field(description="Una frase: por qué esa ruta.")


class Estado(TypedDict, total=False):
    mensaje: str
    ruta: str
    motivo: str
    respuesta: str
    herramientas: list[str]  # herramientas que usó la ruta en este turno (para --saltos)
    messages: Annotated[list[BaseMessage], add_messages]


_llm = None
_generica = None
_tienda_md = None
_preventa = None
_postventa = None


def _router_llm():
    # Se crea al primer uso para que --diagrama funcione sin GOOGLE_API_KEY.
    global _llm
    if _llm is None:
        _llm = ChatGoogleGenerativeAI(model=os.environ["MODELO"], temperature=0).with_structured_output(Decision)
    return _llm


def _generica_llm():
    # Modelo conversacional (sin salida estructurada) para la ruta genérica.
    global _generica
    if _generica is None:
        _generica = ChatGoogleGenerativeAI(model=os.environ["MODELO"], temperature=0)
    return _generica


def _preventa_agent():
    # Agente ReAct (create_agent) con las herramientas de catálogo. Se arma al primer uso.
    global _preventa
    if _preventa is None:
        modelo = ChatGoogleGenerativeAI(model=os.environ["MODELO"], temperature=0)
        _preventa = create_agent(modelo, tools.TOOLS_PREVENTA, system_prompt=prompts.AGENTE_PREVENTA_PROMPT)
    return _preventa


def _postventa_agent():
    # Agente ReAct con las herramientas de pedidos, políticas y reclamos. Se arma al primer uso.
    global _postventa
    if _postventa is None:
        modelo = ChatGoogleGenerativeAI(model=os.environ["MODELO"], temperature=0)
        _postventa = create_agent(modelo, tools.TOOLS_POSTVENTA, system_prompt=prompts.AGENTE_POSTVENTA_PROMPT)
    return _postventa


def _tienda() -> str:
    # Lee data/tienda.md una sola vez y lo cachea.
    global _tienda_md
    if _tienda_md is None:
        ruta = Path(__file__).resolve().parents[2] / "data" / "tienda.md"
        _tienda_md = ruta.read_text(encoding="utf-8")
    return _tienda_md


def _texto_salida(salida) -> str:
    # En langchain-core 1.x el content puede ser un string o una lista de bloques
    # como [{"type": "text", "text": "..."}]. Normaliza ambos casos a texto plano.
    content = getattr(salida, "content", "")
    if isinstance(content, list):
        content = "".join(
            bloque.get("text", "") if isinstance(bloque, dict) else str(bloque)
            for bloque in content
        )
    return (content or "").strip()


def router(estado: Estado) -> Estado:
    humano = HumanMessage(estado["mensaje"])
    historial = estado.get("messages", [])
    ultimos = historial[-4:]  # el router solo mira los últimos 4 mensajes como contexto
    ruta_anterior = estado.get("ruta") or "ninguna"
    pista = SystemMessage(f"Ruta anterior de la conversación: {ruta_anterior}.")
    decision: Decision = _router_llm().invoke([SystemMessage(prompts.ROUTER), pista, *ultimos, humano])
    # herramientas se reinicia cada turno; cada ruta la fija si usó herramientas.
    return {"ruta": decision.ruta, "motivo": decision.motivo, "messages": [humano], "herramientas": []}


def agente_preventa(estado: Estado) -> Estado:
    # Agente ReAct con herramientas de catálogo. Recibe todo el historial (no solo el último).
    try:
        resultado = _preventa_agent().invoke({"messages": estado.get("messages", [])})
        mensajes = resultado["messages"]
        respuesta = _texto_salida(mensajes[-1]) or prompts.PREVENTA_FALLBACK
        # Nombres de las herramientas que llamó, en orden, para mostrarlas en --saltos.
        herramientas = [
            llamada["name"]
            for m in mensajes
            for llamada in (getattr(m, "tool_calls", None) or [])
        ]
    except Exception:
        # Si el modelo falla, no se cae: responde la frase de respaldo.
        logger.exception("El agente de preventa falló")
        respuesta = prompts.PREVENTA_FALLBACK
        herramientas = []
    return {"respuesta": respuesta, "messages": [AIMessage(respuesta)], "herramientas": herramientas}


def agente_postventa(estado: Estado, config) -> Estado:
    # Agente ReAct con herramientas de pedidos/políticas/reclamos. Recibe todo el historial.
    # config trae el thread_id: lo fijamos para que crear_reclamo registre la conversación.
    thread_id = (config or {}).get("configurable", {}).get("thread_id", "desconocido")
    tools.fijar_hilo(thread_id)
    try:
        resultado = _postventa_agent().invoke({"messages": estado.get("messages", [])})
        mensajes = resultado["messages"]
        respuesta = _texto_salida(mensajes[-1]) or prompts.POSTVENTA_FALLBACK
        herramientas = [
            llamada["name"]
            for m in mensajes
            for llamada in (getattr(m, "tool_calls", None) or [])
        ]
    except Exception:
        logger.exception("El agente de postventa falló")
        respuesta = prompts.POSTVENTA_FALLBACK
        herramientas = []
    return {"respuesta": respuesta, "messages": [AIMessage(respuesta)], "herramientas": herramientas}


def respuesta_generica(estado: Estado) -> Estado:
    # El mensaje del usuario ya está en messages (lo agregó el nodo router); se pasa
    # todo el historial para que el asistente use el nombre y el contexto previos.
    historial = estado.get("messages", [])
    sistema = SystemMessage(prompts.RESPUESTA_GENERICA_PROMPT.format(tienda=_tienda()))
    try:
        salida = _generica_llm().invoke([sistema, *historial])
        respuesta = _texto_salida(salida) or prompts.RESPUESTA_GENERICA
    except Exception:
        # Si el modelo no responde, se usa la frase fija de siempre en vez de un error.
        respuesta = prompts.RESPUESTA_GENERICA
    return {"respuesta": respuesta, "messages": [AIMessage(respuesta)]}


def elegir_ruta(estado: Estado) -> str:
    return estado["ruta"]


builder = StateGraph(Estado)
builder.add_node("router", router)
builder.add_node("agente_preventa", agente_preventa)
builder.add_node("agente_postventa", agente_postventa)
builder.add_node("respuesta_generica", respuesta_generica)

builder.add_edge(START, "router")
builder.add_conditional_edges(
    "router",
    elegir_ruta,
    {"preventa": "agente_preventa", "postventa": "agente_postventa", "generica": "respuesta_generica"},
)
builder.add_edge("agente_preventa", END)
builder.add_edge("agente_postventa", END)
builder.add_edge("respuesta_generica", END)


# Re-exportado para que main.py pueda abrir la misma memoria que la API.
from src.router.memoria import abrir_checkpointer  # noqa: E402


def construir_grafo(checkpointer):
    """Compila el grafo con el checkpointer dado (Postgres o RAM).

    La API y el CLI lo llaman con el checkpointer que entrega `abrir_checkpointer`.
    """
    return builder.compile(checkpointer=checkpointer)


# Grafo por defecto con memoria RAM: lo usan `--diagrama` y las pruebas,
# que no necesitan persistencia. La API y el CLI usan `construir_grafo`.
graph = builder.compile(checkpointer=MemorySaver())
