"""Ver la memoria persistente del router (checkpointer de LangGraph).

Uso (desde la raíz del proyecto):
    python scripts/ver_memoria.py            -> lista los hilos guardados
    python scripts/ver_memoria.py <thread>   -> imprime la conversación de ese hilo

Lee DATABASE_URL del .env. Si no hay Postgres, no hay nada persistente que mostrar.
"""

import os
import sys

# Permite importar `src...` al correr el script directamente.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

from src.router.memoria import abrir_checkpointer

load_dotenv()

ETIQUETA = {"human": "cliente", "ai": "agente", "system": "sistema", "tool": "tool"}


def _rol(mensaje) -> str:
    tipo = getattr(mensaje, "type", None) or "?"
    return ETIQUETA.get(tipo, tipo)


def _contenido(mensaje) -> str:
    cont = getattr(mensaje, "content", mensaje)
    return cont if isinstance(cont, str) else str(cont)


def listar_hilos(checkpointer) -> None:
    """Lista los hilos con su número de checkpoints y la fecha del último."""
    hilos: dict[str, dict] = {}
    for tup in checkpointer.list(None):
        tid = tup.config["configurable"]["thread_id"]
        ts = tup.checkpoint.get("ts", "")
        datos = hilos.setdefault(tid, {"n": 0, "ultimo": ""})
        datos["n"] += 1
        if ts > datos["ultimo"]:
            datos["ultimo"] = ts

    if not hilos:
        print("No hay hilos guardados.")
        return

    print(f"{'HILO':<24} {'CHECKPOINTS':>11}  ÚLTIMO")
    print("-" * 60)
    for tid, d in sorted(hilos.items()):
        print(f"{tid:<24} {d['n']:>11}  {d['ultimo']}")


def imprimir_conversacion(checkpointer, thread_id: str) -> None:
    """Imprime los mensajes de un hilo en orden."""
    tup = checkpointer.get_tuple({"configurable": {"thread_id": thread_id}})
    if tup is None:
        print(f"No hay memoria para el hilo '{thread_id}'.")
        return

    mensajes = (tup.checkpoint.get("channel_values") or {}).get("messages") or []
    if not mensajes:
        print(f"El hilo '{thread_id}' existe pero no tiene mensajes.")
        return

    print(f"Conversación del hilo '{thread_id}' ({len(mensajes)} mensajes):\n")
    for m in mensajes:
        print(f"[{_rol(m)}] {_contenido(m)}")


def main() -> None:
    args = sys.argv[1:]
    with abrir_checkpointer() as (checkpointer, tipo):
        if tipo != "postgres":
            print("Sin memoria persistente: define DATABASE_URL (Postgres) para guardar/leer hilos.")
            return
        if args:
            imprimir_conversacion(checkpointer, args[0])
        else:
            listar_hilos(checkpointer)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
