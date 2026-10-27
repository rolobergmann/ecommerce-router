"""Registra el webhook de Telegram apuntando a PUBLIC_URL/telegram.

Lee TELEGRAM_TOKEN, TELEGRAM_SECRET y PUBLIC_URL del entorno (.env).
Uso desde la raíz: python scripts/set_webhook.py
"""

import os

import httpx
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.environ["TELEGRAM_TOKEN"]
SECRET = os.environ["TELEGRAM_SECRET"]
PUBLIC_URL = os.environ["PUBLIC_URL"].rstrip("/")


def main() -> None:
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
    payload = {"url": f"{PUBLIC_URL}/telegram", "secret_token": SECRET}
    r = httpx.post(url, json=payload, timeout=10)
    print(r.status_code, r.json())


if __name__ == "__main__":
    main()
