"""Muestra el estado del webhook de Telegram (getWebhookInfo).

Sirve para confirmar que el webhook quedó bien y ver si hay errores pendientes.
Uso desde la raíz: python scripts/webhook_info.py
"""

import json
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.environ["TELEGRAM_TOKEN"]


def main() -> None:
    url = f"https://api.telegram.org/bot{TOKEN}/getWebhookInfo"
    r = httpx.get(url, timeout=10)
    print(json.dumps(r.json(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
