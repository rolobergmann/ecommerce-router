"""Ejecuta un agente desde la raíz: python main.py {nombre_agente} "mensaje" [--saltos] [--diagrama] [--hilo NOMBRE].

Usa la MISMA memoria que la API: si hay DATABASE_URL, las conversaciones se guardan
en Postgres (sobreviven a reinicios); si no, quedan en RAM.
"""

import argparse
import importlib
import sys


def _ejecutar(graph, args) -> None:
    config = {"configurable": {"thread_id": args.hilo}}
    saltos = []
    for paso in graph.stream({"mensaje": args.mensaje}, config, stream_mode="updates"):
        # Cada nodo aporta su nombre y, si usó herramientas en ESTE turno, sus nombres.
        # Se leen del update del nodo (no del estado acumulado), para que --saltos salga
        # limpio aunque el hilo tenga historial: "router → agente_preventa → buscar_productos".
        for nodo, update in paso.items():
            saltos.append(nodo)
            if isinstance(update, dict):
                saltos.extend(update.get("herramientas") or [])
    final = graph.get_state(config).values

    if args.saltos:
        print("Saltos:", " → ".join(saltos))
        if final.get("motivo"):
            print("Motivo:", final["motivo"])
        print()
    print(final.get("respuesta", ""))


def main() -> None:
    parser = argparse.ArgumentParser(description="Ejecuta un agente de src/.")
    parser.add_argument("agente", help="Nombre de la carpeta en src/, por ejemplo: router")
    parser.add_argument("mensaje", nargs="?", help="Mensaje para el agente")
    parser.add_argument("--saltos", action="store_true", help="Imprime los nodos por los que pasó el grafo")
    parser.add_argument("--diagrama", action="store_true", help="Imprime el Mermaid del grafo sin ejecutarlo")
    parser.add_argument("--hilo", default="cli", help="thread_id para la memoria (por defecto: cli)")
    args = parser.parse_args()

    modulo = importlib.import_module(f"src.{args.agente}.graph")

    if args.diagrama:
        # El diagrama no necesita memoria; usa el grafo por defecto (RAM).
        print(modulo.graph.get_graph().draw_mermaid())
        return

    if not args.mensaje:
        parser.error("falta el mensaje")

    abrir = getattr(modulo, "abrir_checkpointer", None)
    construir = getattr(modulo, "construir_grafo", None)

    if abrir and construir:
        # Abre la misma memoria que la API (Postgres o RAM) solo para esta ejecución.
        with abrir() as (checkpointer, _tipo):
            _ejecutar(construir(checkpointer), args)
    else:
        # Agente sin memoria configurable: usa su grafo por defecto.
        _ejecutar(modulo.graph, args)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
