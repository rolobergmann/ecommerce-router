"""Ejecuta un agente desde la raíz: python main.py {nombre_agente} "mensaje" [--saltos] [--diagrama]."""

import argparse
import importlib
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="Ejecuta un agente de src/.")
    parser.add_argument("agente", help="Nombre de la carpeta en src/, por ejemplo: router")
    parser.add_argument("mensaje", nargs="?", help="Mensaje para el agente")
    parser.add_argument("--saltos", action="store_true", help="Imprime los nodos por los que pasó el grafo")
    parser.add_argument("--diagrama", action="store_true", help="Imprime el Mermaid del grafo sin ejecutarlo")
    parser.add_argument("--thread", default="cli", help="thread_id para la memoria (por defecto: cli)")
    args = parser.parse_args()

    graph = importlib.import_module(f"src.{args.agente}.graph").graph

    if args.diagrama:
        print(graph.get_graph().draw_mermaid())
        return

    if not args.mensaje:
        parser.error("falta el mensaje")

    config = {"configurable": {"thread_id": args.thread}}
    saltos = []
    for paso in graph.stream({"mensaje": args.mensaje}, config, stream_mode="updates"):
        saltos.extend(paso.keys())
    final = graph.get_state(config).values

    if args.saltos:
        print("Saltos:", " → ".join(saltos))
        if final.get("motivo"):
            print("Motivo:", final["motivo"])
        print()
    print(final.get("respuesta", ""))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
