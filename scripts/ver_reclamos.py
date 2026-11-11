"""Lista los reclamos de postventa guardados.

Uso (desde la raíz del proyecto):
    python scripts/ver_reclamos.py

Lee de Postgres con DATABASE_URL (la misma base del checkpointer). Sin base, no hay
reclamos persistentes que mostrar.
"""

import os
import sys

# Permite importar `src...` al correr el script directamente.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

from src.router import reclamos

load_dotenv()


def main() -> None:
    filas = reclamos.listar()
    if not filas:
        print("No hay reclamos registrados.")
        return

    print(f"{len(filas)} reclamo(s):\n")
    for r in filas:
        print(f"[{r.get('ticket')}]  pedido {r.get('numero_pedido')}  ·  motivo: {r.get('motivo')}")
        detalle = (r.get("detalle") or "").strip()
        if detalle:
            print(f"    detalle: {detalle}")
        print(f"    hilo: {r.get('thread_id')}  ·  creado: {r.get('creado_en')}")
        print()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
