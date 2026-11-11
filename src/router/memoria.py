"""Memoria (checkpointer) del router.

Decide dónde se guardan las conversaciones del grafo:

- Si hay `DATABASE_URL`, usa **Postgres** (`PostgresSaver`): sobrevive a reinicios.
- Si no, o si Postgres no responde al arrancar, cae a **RAM** (`MemorySaver`):
  funciona igual, pero se olvida todo al reiniciar el proceso.

Está pensado para abrirse UNA vez (al arrancar la API o al correr el CLI) y
cerrarse al terminar, por eso se expone como *context manager*.

La API invoca el grafo de forma **síncrona** (`graph.invoke` en endpoints `def`),
así que aquí se usa el `PostgresSaver` síncrono, no la variante async.
"""

import logging
import os
from contextlib import contextmanager

from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger("router.memoria")


@contextmanager
def abrir_checkpointer():
    """Entrega `(checkpointer, tipo)` donde `tipo` es "postgres" o "ram".

    Uso:
        with abrir_checkpointer() as (checkpointer, tipo):
            graph = construir_grafo(checkpointer)
            ...
    """
    url = os.getenv("DATABASE_URL")

    if not url:
        logger.info("DATABASE_URL no definida: memoria en RAM (MemorySaver).")
        yield MemorySaver(), "ram"
        return

    # Import perezoso: así, sin DATABASE_URL, no exigimos los paquetes de Postgres.
    try:
        from langgraph.checkpoint.postgres import PostgresSaver
        from psycopg_pool import ConnectionPool
    except Exception:
        logger.exception("Faltan paquetes de Postgres: memoria en RAM (MemorySaver).")
        yield MemorySaver(), "ram"
        return

    pool = None
    try:
        pool = ConnectionPool(
            conninfo=url,
            min_size=1,
            max_size=2,  # la base puede ser compartida por todo el curso: pocas conexiones
            open=False,
            check=ConnectionPool.check_connection,  # revisa cada conexión antes de usarla
            kwargs={"autocommit": True, "prepare_threshold": 0, "connect_timeout": 10},
        )
        pool.open(wait=True, timeout=10)  # se abre una vez; falla rápido si la base no responde
        checkpointer = PostgresSaver(pool)
        checkpointer.setup()  # crea sus tablas si no existen
        logger.info("Memoria en Postgres (PostgresSaver).")
    except Exception:
        logger.exception("No se pudo iniciar Postgres: memoria en RAM (MemorySaver).")
        if pool is not None:
            try:
                pool.close()
            except Exception:
                pass
        yield MemorySaver(), "ram"
        return

    try:
        yield checkpointer, "postgres"
    finally:
        pool.close()  # se cierra al apagar la API / terminar el CLI
        logger.info("Pool de Postgres cerrado.")
