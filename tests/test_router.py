"""Pruebas del router: cada caso se reporta por separado y se exige un mínimo de aciertos.

El modelo no es determinista, así que un caso fallado no rompe la suite (sale como xfail);
lo que sí la rompe es bajar de MINIMO_ACIERTOS.
"""

import json
from pathlib import Path

import pytest

from src.router.graph import graph

CASOS = json.loads((Path(__file__).parent / "casos_router.json").read_text(encoding="utf-8"))
MINIMO_ACIERTOS = 13

_resultados: dict[int, str] = {}


def ruta_obtenida(i: int) -> str:
    # Cada caso se ejecuta una sola vez aunque lo usen los dos tests.
    if i not in _resultados:
        config = {"configurable": {"thread_id": f"pytest-{i}"}}
        _resultados[i] = graph.invoke({"mensaje": CASOS[i]["mensaje"]}, config)["ruta"]
    return _resultados[i]


# ids cortos: pytest escapa los acentos y los mensajes completos quedarían ilegibles.
@pytest.mark.parametrize("i", range(len(CASOS)), ids=[f"{c['esperado']}-{i % 5 + 1}" for i, c in enumerate(CASOS)])
def test_caso(i):
    obtenido = ruta_obtenida(i)
    if obtenido != CASOS[i]["esperado"]:
        pytest.xfail(f"esperado {CASOS[i]['esperado']}, obtenido {obtenido}")


def test_minimo_aciertos():
    aciertos = sum(ruta_obtenida(i) == c["esperado"] for i, c in enumerate(CASOS))
    assert aciertos >= MINIMO_ACIERTOS, f"{aciertos}/{len(CASOS)} aciertos, mínimo {MINIMO_ACIERTOS}"
