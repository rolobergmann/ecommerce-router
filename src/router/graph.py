"""Grafo del agente router: clasifica el mensaje y lo deriva a preventa, postventa o genérica."""

import os
import warnings
from typing import Annotated, Literal, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from src.router import prompts

load_dotenv()

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
    messages: Annotated[list[BaseMessage], add_messages]


_llm = None


def _router_llm():
    # Se crea al primer uso para que --diagrama funcione sin GOOGLE_API_KEY.
    global _llm
    if _llm is None:
        _llm = ChatGoogleGenerativeAI(model=os.environ["MODELO"], temperature=0).with_structured_output(Decision)
    return _llm


def router(estado: Estado) -> Estado:
    humano = HumanMessage(estado["mensaje"])
    historial = estado.get("messages", [])
    decision: Decision = _router_llm().invoke([SystemMessage(prompts.ROUTER), *historial, humano])
    return {"ruta": decision.ruta, "motivo": decision.motivo, "messages": [humano]}


def agente_preventa(estado: Estado) -> Estado:
    respuesta = prompts.AGENTE_PREVENTA.format(mensaje=estado["mensaje"])
    return {"respuesta": respuesta, "messages": [AIMessage(respuesta)]}


def agente_postventa(estado: Estado) -> Estado:
    respuesta = prompts.AGENTE_POSTVENTA.format(mensaje=estado["mensaje"])
    return {"respuesta": respuesta, "messages": [AIMessage(respuesta)]}


def respuesta_generica(estado: Estado) -> Estado:
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

graph = builder.compile(checkpointer=MemorySaver())
