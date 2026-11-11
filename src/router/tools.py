"""Herramientas del agente de preventa: consultan el catálogo (solo lectura).

Cada herramienta arma un SELECT con parámetros (nunca concatenando texto del
usuario o del modelo) y, si la base no responde, devuelve "Catálogo no disponible".
"""

from decimal import Decimal

from langchain_core.tools import tool

from src.router import catalogo

VISTA = "catalogo.productos_unicos"


def _num(valor):
    """Normaliza Decimal a int/float; deja None como None."""
    if valor is None:
        return None
    if isinstance(valor, Decimal):
        return int(valor) if valor == valor.to_integral_value() else float(valor)
    return valor


def _resumen(fila: dict) -> dict:
    """Campos cortos de un producto (para listados)."""
    return {
        "sku_id": fila.get("sku_id"),
        "nombre": fila.get("nombre"),
        "marca": fila.get("marca") or None,
        "precio_internet": _num(fila.get("precio_internet")),
        "descuento_pct": _num(fila.get("descuento_pct")),
        "rating": _num(fila.get("rating")),
    }


@tool
def buscar_productos(consulta: str, categoria: str = "", marca: str = "", precio_max: int | None = None):
    """Busca productos en el catálogo por palabras del nombre.

    - consulta: cada palabra debe aparecer en el nombre (sin distinguir mayúsculas).
    - categoria: opcional, "Smartphones" o "Televisores".
    - marca: opcional; se busca en la columna marca o dentro del nombre (muchas filas
      no traen marca).
    - precio_max: opcional, precio máximo en pesos (precio_internet <= precio_max).

    Devuelve hasta 5 productos, primero los de mejor rating, con sku_id, nombre,
    marca, precio_internet, descuento_pct y rating. Para el link usa ver_producto.
    """
    where: list[str] = []
    params: list = []
    for palabra in consulta.split():
        where.append("nombre ILIKE %s")
        params.append(f"%{palabra}%")
    if categoria:
        where.append("categoria ILIKE %s")
        params.append(f"%{categoria}%")
    if marca:
        where.append("(marca ILIKE %s OR nombre ILIKE %s)")
        params.extend([f"%{marca}%", f"%{marca}%"])
    if precio_max is not None:
        where.append("precio_internet <= %s")
        params.append(precio_max)

    clausula = " AND ".join(where) if where else "TRUE"
    sql = (
        "SELECT sku_id, nombre, marca, precio_internet, descuento_pct, rating "
        f"FROM {VISTA} WHERE {clausula} "
        "ORDER BY rating DESC NULLS LAST LIMIT 5"
    )
    try:
        filas = catalogo.consultar(sql, params)
    except catalogo.CatalogoNoDisponible:
        return "Catálogo no disponible"
    if not filas:
        return "Sin resultados en el catálogo para esa búsqueda."
    return [_resumen(f) for f in filas]


@tool
def ver_producto(sku_id: str):
    """Devuelve el detalle completo de un producto por su sku_id, incluido el link."""
    sql = (
        "SELECT sku_id, nombre, marca, categoria, subcategoria, precio_normal, "
        "precio_internet, descuento_pct, rating, tienda_oficial, link, imagen "
        f"FROM {VISTA} WHERE sku_id = %s LIMIT 1"
    )
    try:
        filas = catalogo.consultar(sql, [sku_id])
    except catalogo.CatalogoNoDisponible:
        return "Catálogo no disponible"
    if not filas:
        return "No encontré ese producto."

    fila = filas[0]
    detalle = _resumen(fila)
    detalle.update(
        {
            "categoria": fila.get("categoria"),
            "subcategoria": fila.get("subcategoria") or None,
            "precio_normal": _num(fila.get("precio_normal")),
            "tienda_oficial": fila.get("tienda_oficial"),
            "link": fila.get("link"),
            "imagen": fila.get("imagen"),
        }
    )
    return detalle


@tool
def mejores_ofertas(categoria: str = "", limite: int = 5):
    """Devuelve los productos con mayor descuento_pct (hasta `limite`, por defecto 5).

    categoria es opcional ("Smartphones" o "Televisores"). Incluye sku_id, nombre,
    marca, precio_internet, descuento_pct y rating.
    """
    where = ["descuento_pct IS NOT NULL"]
    params: list = []
    if categoria:
        where.append("categoria ILIKE %s")
        params.append(f"%{categoria}%")

    clausula = " AND ".join(where)
    sql = (
        "SELECT sku_id, nombre, marca, precio_internet, descuento_pct, rating "
        f"FROM {VISTA} WHERE {clausula} "
        "ORDER BY descuento_pct DESC NULLS LAST LIMIT %s"
    )
    params.append(limite)
    try:
        filas = catalogo.consultar(sql, params)
    except catalogo.CatalogoNoDisponible:
        return "Catálogo no disponible"
    if not filas:
        return "Sin ofertas disponibles."
    return [_resumen(f) for f in filas]


TOOLS = [buscar_productos, ver_producto, mejores_ofertas]
