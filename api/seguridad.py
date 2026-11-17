"""Control de acceso de la API por token (configurable por entorno).

Uso: se protege un endpoint agregándole `dependencies=[Depends(verificar_token)]`.

- El token se lee de la variable de entorno `API_TOKEN`.
- Si `API_TOKEN` está definido, el cliente DEBE enviar `Authorization: Bearer <API_TOKEN>`;
  si falta o no coincide, responde 401.
- Si `API_TOKEN` NO está definido, el acceso queda abierto (modo desarrollo) y se asume
  que el operador no activó la protección. Para la entrega se define `API_TOKEN`.

El token nunca va en el código ni en el repo: solo en `.env` (local) o en los Config Vars
del servidor. En `.env.example` se documenta con un valor ficticio.
"""

import os

from fastapi import Header, HTTPException


def verificar_token(authorization: str | None = Header(default=None)) -> None:
    # Se lee en cada request para respetar el .env ya cargado al arrancar la app.
    token = os.getenv("API_TOKEN", "")
    if not token:
        return  # sin token configurado: acceso abierto (desarrollo)
    if authorization != f"Bearer {token}":
        raise HTTPException(status_code=401, detail="Token de acceso inválido o ausente.")
