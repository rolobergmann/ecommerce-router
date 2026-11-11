"""Almacén de reclamos de postventa.

Los reclamos se guardan en **Postgres** (tabla `reclamos`, misma DATABASE_URL que el
checkpointer), creada al arrancar si no existe. En Heroku el disco se borra en cada
reinicio, por eso NO se usan archivos. Si no hay base, se guardan en memoria (se
pierden al reiniciar) y se avisa en el log.
"""

import logging
import os
import threading
import uuid
from datetime import datetime, timezone

logger = logging.getLogger("router.reclamos")


class SinBase(Exception):
    """No hay DATABASE_URL configurada."""


_memoria: list[dict] = []
_lock = threading.Lock()
_tabla_ok = False


def _ejecutar(sql: str, params=(), fetch: bool = False):
    """Ejecuta SQL contra Postgres abriendo y cerrando la conexión (no deja abiertas)."""
    url = os.getenv("DATABASE_URL")
    if not url:
        raise SinBase("DATABASE_URL no está definida.")

    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(url, connect_timeout=10, autocommit=True) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            if fetch:
                return cur.fetchall()
    return None


def asegurar_tabla() -> bool:
    """Crea la tabla `reclamos` si no existe. Devuelve True si Postgres está disponible."""
    global _tabla_ok
    if _tabla_ok:
        return True
    try:
        _ejecutar(
            """
            CREATE TABLE IF NOT EXISTS reclamos (
                ticket TEXT PRIMARY KEY,
                numero_pedido TEXT,
                motivo TEXT,
                detalle TEXT,
                thread_id TEXT,
                creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        _tabla_ok = True
        logger.info("Tabla de reclamos lista (Postgres).")
        return True
    except SinBase:
        logger.warning("Sin DATABASE_URL: los reclamos quedan en memoria (se pierden al reiniciar).")
        return False
    except Exception:
        logger.exception("No se pudo preparar la tabla de reclamos; se usará memoria.")
        return False


def guardar(numero_pedido: str, motivo: str, detalle: str, thread_id: str) -> str:
    """Guarda un reclamo y devuelve su número de ticket."""
    ticket = "REC-" + uuid.uuid4().hex[:8].upper()
    creado = datetime.now(timezone.utc)

    if asegurar_tabla():
        try:
            _ejecutar(
                "INSERT INTO reclamos (ticket, numero_pedido, motivo, detalle, thread_id, creado_en) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (ticket, numero_pedido, motivo, detalle, thread_id, creado),
            )
            return ticket
        except Exception:
            logger.exception("No se pudo guardar el reclamo en Postgres; queda en memoria.")

    with _lock:
        _memoria.append(
            {
                "ticket": ticket,
                "numero_pedido": numero_pedido,
                "motivo": motivo,
                "detalle": detalle,
                "thread_id": thread_id,
                "creado_en": creado,
            }
        )
    logger.warning("Reclamo %s guardado solo en memoria (sin persistencia).", ticket)
    return ticket


def listar() -> list[dict]:
    """Lista los reclamos (de Postgres si hay; si no, los de memoria)."""
    try:
        filas = _ejecutar(
            "SELECT ticket, numero_pedido, motivo, detalle, thread_id, creado_en "
            "FROM reclamos ORDER BY creado_en DESC",
            fetch=True,
        )
        return filas or []
    except SinBase:
        with _lock:
            return list(_memoria)
    except Exception:
        logger.exception("No se pudieron leer los reclamos de Postgres")
        with _lock:
            return list(_memoria)
