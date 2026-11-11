"""Ver el catálogo de la tienda desde la terminal.

Uso (desde la raíz del proyecto):
    python scripts/ver_catalogo.py "texto"   -> hasta 10 productos cuyo nombre contenga ese texto
    python scripts/ver_catalogo.py            -> cuántos productos hay por categoría

Lee DATABASE_URL del .env (la misma base del catálogo y la memoria).
"""

import os
import sys

# Permite importar `src...` al correr el script directamente.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

from src.router import catalogo

load_dotenv()


def _miles(valor) -> str:
    try:
        return f"{int(valor):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "s/d"


def buscar(texto: str) -> None:
    sql = (
        "SELECT nombre, precio_internet, rating FROM catalogo.productos_unicos "
        "WHERE nombre ILIKE %s ORDER BY rating DESC NULLS LAST LIMIT 10"
    )
    filas = catalogo.consultar(sql, [f"%{texto}%"])
    if not filas:
        print(f"Sin productos cuyo nombre contenga '{texto}'.")
        return
    print(f"Hasta 10 productos con '{texto}' en el nombre:\n")
    for f in filas:
        rating = f.get("rating")
        rating_txt = f"{float(rating):.1f}" if rating is not None else "s/d"
        print(f"  ${_miles(f.get('precio_internet'))}  ·  rating {rating_txt}  ·  {f.get('nombre')}")


def por_categoria() -> None:
    sql = (
        "SELECT categoria, COUNT(*) AS n FROM catalogo.productos_unicos "
        "GROUP BY categoria ORDER BY categoria"
    )
    filas = catalogo.consultar(sql)
    if not filas:
        print("El catálogo está vacío.")
        return
    print("Productos por categoría:\n")
    for f in filas:
        print(f"  {f.get('categoria') or '(sin categoría)'}: {f.get('n')}")


def main() -> None:
    args = sys.argv[1:]
    try:
        if args:
            buscar(args[0])
        else:
            por_categoria()
    except catalogo.CatalogoNoDisponible:
        print("Catálogo no disponible: revisa DATABASE_URL o la conexión a Postgres.")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
