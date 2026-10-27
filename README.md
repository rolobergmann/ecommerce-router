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

> Se completa en la **parte 5** del curso; la ruta `/telegram` por ahora acepta cualquier JSON
> y responde `{"ok": true}`.

Flujo previsto: crear el bot con **@BotFather** (`/newbot`) para obtener `TELEGRAM_TOKEN`,
elegir un `TELEGRAM_SECRET`, registrar el webhook apuntando a `PUBLIC_URL/telegram` con ese
secreto, y hacer que `/telegram` lea `chat_id` y `text` del update, invoque el grafo y responda
con `sendMessage`.
