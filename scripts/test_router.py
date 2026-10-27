"""Corre el router con los casos de tests/casos_router.json y muestra una tabla de resultados.

Uso desde la raíz: python scripts/test_router.py
"""

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from src.router.graph import graph  # noqa: E402


def corto(texto: str, ancho: int) -> str:
    return texto if len(texto) <= ancho else texto[: ancho - 1] + "…"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    casos = json.loads((RAIZ / "tests" / "casos_router.json").read_text(encoding="utf-8"))

    print(f"{'Mensaje':<45} {'Esperado':<10} {'Obtenido':<10} OK  Motivo")
    print("-" * 120)

    fallados = []
    for i, caso in enumerate(casos):
        config = {"configurable": {"thread_id": f"script-{i}"}}
        final = graph.invoke({"mensaje": caso["mensaje"]}, config)
        ok = final["ruta"] == caso["esperado"]
        if not ok:
            fallados.append((caso, final))
        print(
            f"{corto(caso['mensaje'], 45):<45} {caso['esperado']:<10} {final['ruta']:<10} "
            f"{'✔' if ok else '✘'}   {final['motivo']}"
        )

    aciertos = len(casos) - len(fallados)
    print("-" * 120)
    print(f"Aciertos: {aciertos}/{len(casos)} ({aciertos / len(casos):.0%})")

    if fallados:
        print("\nFallados:")
        for caso, final in fallados:
            print(f"- \"{caso['mensaje']}\": esperado {caso['esperado']}, obtenido {final['ruta']} ({final['motivo']})")


if __name__ == "__main__":
    main()
