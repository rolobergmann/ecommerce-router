"""Acceso de SOLO LECTURA al catálogo de la tienda (Postgres).

El catálogo vive en la vista `catalogo.productos_unicos`, en la misma base que usa
el checkpointer (variable DATABASE_URL). Aquí solo se leen productos:

- Siempre SELECT; nunca se escribe.
- El SQL va siempre con **parámetros**: nunca se arma concatenando texto que venga
  del usuario o del modelo.
- La conexión se abre y se cierra en cada consulta (no se dejan conexiones abiertas;
  el usuario de la base admite pocas).
- Si la base no responde, se lanza `CatalogoNoDisponible` para que la herramienta lo
  informe sin tumbar la API.
"""

import logging
import os

logger = logging.getLogger("router.catalogo")


class CatalogoNoDisponible(Exception):
    """La base no respondió o no está configurada."""


def consultar(sql: str, params=()) -> list[dict]:
    """Ejecuta un SELECT parametrizado y devuelve las filas como diccionarios."""
    if not sql.lstrip().upper().startswith(("SELECT", "WITH")):
        raise ValueError("Solo se permiten consultas SELECT.")

    url = os.getenv("DATABASE_URL")
    if not url:
        raise CatalogoNoDisponible("DATABASE_URL no está definida.")

    try:
        import psycopg
        from psycopg.rows import dict_row

        # `with psycopg.connect(...)` cierra la conexión al salir del bloque.
        with psycopg.connect(url, connect_timeout=10) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql, params)
                return cur.fetchall()
    except CatalogoNoDisponible:
        raise
    except Exception as exc:
        logger.exception("El catálogo (Postgres) no respondió")
        raise CatalogoNoDisponible(str(exc))
