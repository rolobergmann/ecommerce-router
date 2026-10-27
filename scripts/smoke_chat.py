"""Manda los 6 mensajes del router a la API /chat y muestra la ruta de cada uno.

Sirve para validar el ruteo end-to-end (HTTP), en local o en Heroku, de una sola pasada.

URL base (en este orden de prioridad):
    1. argumento:   python scripts/smoke_chat.py https://mi-app.herokuapp.com
    2. PUBLIC_URL del .env
    3. http://localhost:8000
"""

import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

CASOS = [
    {"mensaje": "¿tienen la polera azul en talla M?", "esperado": "preventa"},
    {"mensaje": "mi pedido 4521 llegó roto", "esperado": "postventa"},
    {"mensaje": "hola", "esperado": "generica"},
    {"mensaje": "¿cuánto cuesta el envío a Valparaíso?", "esperado": "preventa"},
    {"mensaje": "quiero devolver unas zapatillas", "esperado": "postventa"},
    {"mensaje": "¿qué hora es en Tokio?", "esperado": "generica"},
]


def base_url() -> str:
    if len(sys.argv) > 1:
        return sys.argv[1].rstrip("/")
    return os.getenv("PUBLIC_URL", "http://localhost:8000").rstrip("/")


def corto(texto: str, ancho: int) -> str:
    return texto if len(texto) <= ancho else texto[: ancho - 1] + "…"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    url = f"{base_url()}/chat"
    print(f"POST {url}\n")
    print(f"{'Mensaje':<42} {'Esperado':<10} {'Obtenido':<12} OK  Motivo")
    print("-" * 110)

    aciertos = 0
    fallados = []
    for i, caso in enumerate(CASOS):
        payload = {"user_id": f"smoke-{i}", "texto": caso["mensaje"]}
        try:
            r = httpx.post(url, json=payload, timeout=30)
        except Exception as e:
            print(f"{corto(caso['mensaje'], 42):<42} {caso['esperado']:<10} {'ERROR':<12} ✘   {e}")
            fallados.append(caso["mensaje"])
            continue

        if r.status_code == 200:
            data = r.json()
            obtenido, motivo = data["ruta"], data["motivo"]
            ok = obtenido == caso["esperado"]
            aciertos += ok
            if not ok:
                fallados.append(caso["mensaje"])
        else:
            # 502 = el modelo falló (p. ej. créditos agotados); 422 = body inválido.
            detalle = r.json().get("detail", "") if r.headers.get("content-type", "").startswith("application/json") else r.text
            obtenido, motivo, ok = f"HTTP {r.status_code}", detalle, False
            fallados.append(caso["mensaje"])

        print(f"{corto(caso['mensaje'], 42):<42} {caso['esperado']:<10} {obtenido:<12} {'✔' if ok else '✘'}   {corto(str(motivo), 45)}")

    print("-" * 110)
    print(f"Aciertos: {aciertos}/{len(CASOS)} ({aciertos / len(CASOS):.0%})")
    if fallados:
        print("Fallados/errores:")
        for m in fallados:
            print(f"- {m}")


if __name__ == "__main__":
    main()
