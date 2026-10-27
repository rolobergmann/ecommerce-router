# Ecommerce Router API

Chat de atención de un ecommerce construido con **LangGraph** y servido con **FastAPI**.
Un nodo *router* clasifica cada mensaje y lo deriva a uno de tres agentes: **preventa**,
**postventa** o **genérica**. Por ahora los agentes destino son cascarones; lo que importa
es que el router enrute bien.

## Requisitos

- Python 3.12
- Una `GOOGLE_API_KEY` de Google AI Studio (Gemini)

## Configuración

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows PowerShell
pip install -r requirements.txt
```

Copia `.env.example` a `.env` y rellena al menos `GOOGLE_API_KEY`. Nunca subas `.env` al repo.

## Correr el router en local (CLI)

```bash
python main.py router "¿tienen la polera azul en talla M?"
python main.py router "mi pedido 4521 llegó roto" --saltos
python main.py router --diagrama
```

## Levantar la API

```bash
uvicorn api.app:app --reload --port 8000
```

- Swagger / documentación interactiva: http://localhost:8000/docs
- Estado: http://localhost:8000/health

### Ejemplo con curl

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"user_id\": \"cliente-123\", \"texto\": \"¿tienen la polera azul en talla M?\"}"
```

Respuesta:

```json
{
  "ruta": "preventa",
  "motivo": "El cliente pregunta por la talla de un producto antes de comprar.",
  "respuesta": "Soy el agente de preventa. Recibí: ¿tienen la polera azul en talla M?. Pronto podré ayudarte con productos y compras."
}
```

## Pruebas

```bash
python scripts/test_router.py   # tabla de aciertos sobre 15 casos
pytest                          # exige al menos 13/15 aciertos
```

## Bruno

La carpeta `bruno/` trae una colección con `health`, `chat-preventa`, `chat-postventa` y
`chat-generica`. La URL base está en la variable de entorno `baseUrl`: elige el entorno
`local` o `heroku` en Bruno para cambiar de servidor.

## Despliegue en Heroku

El repo se despliega tal cual: Heroku construye desde `requirements.txt`, usa `.python-version`
(3.12) y arranca con el `Procfile`:

```
web: uvicorn api.app:app --host 0.0.0.0 --port $PORT
```

Pasos (desde el panel https://dashboard.heroku.com):

1. **New → Create new app**: nombre único (será la URL `https://<nombre>.herokuapp.com`) y región.
2. **Deploy → Deployment method → GitHub**: conecta este repo.
3. **Settings → Reveal Config Vars**: agrega una por una las variables del `.env`
   (`GOOGLE_API_KEY`, `MODELO`, `PUBLIC_URL`). Las de Telegram se agregan en el paso de Telegram.
   **Nunca** subas el `.env` al repo; las claves van solo como Config Vars.
4. **Deploy → Manual deploy → main → Deploy Branch**.
5. **Comprobar**: `Open app` → `/health` y `/docs`.

## Conectar Telegram

El bot se conecta **sin librerías de bot**, solo con `httpx`. Telegram manda cada mensaje a
`PUBLIC_URL/telegram`; la API valida el secreto, invoca el grafo y responde con `sendMessage`.

1. **Crear el bot**: habla con **@BotFather** (`/newbot`), copia el token a `TELEGRAM_TOKEN`
   en `.env` y elige un `TELEGRAM_SECRET` (cualquier cadena secreta).
2. **Config Vars en Heroku**:

   ```bash
   heroku config:set TELEGRAM_TOKEN=... TELEGRAM_SECRET=... --app ecommerce-rbp
   ```

3. **Subir los cambios** a GitHub (y a Heroku, si no tienes Automatic Deploys):

   ```bash
   git add -A
   git commit -m "telegram: webhook y sendMessage"
   git push
   ```

4. **Registrar el webhook** y confirmarlo (con `PUBLIC_URL` apuntando a tu app de Heroku):

   ```bash
   python scripts/set_webhook.py     # setWebhook con url y secret_token
   python scripts/webhook_info.py    # getWebhookInfo: confirma que quedó bien
   ```

5. **Probar**: escribe al bot los 6 mensajes del router y revisa en los logs qué ruta tomó cada uno:

   ```bash
   heroku logs --tail --app ecommerce-rbp
   ```

**Si el bot no responde**, revisa: el webhook apunta a **https** (no http), el `TELEGRAM_SECRET`
es **igual** en Heroku y en el webhook, y el `TELEGRAM_TOKEN` es correcto. `webhook_info.py`
muestra el último error pendiente.

> **Probar en local sin desplegar (opcional):** levanta un túnel con
> `cloudflared tunnel --url http://localhost:8000`, usa esa URL https como `PUBLIC_URL`,
> corre `set_webhook.py` y prueba el bot contra tu máquina.
