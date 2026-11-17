# Ecommerce Router — Agente de atención (Curso 2, Taller de implementación)

Agente de atención para un ecommerce de **televisores y celulares** (tienda ficticia *ElectroMax*).
Un **router** (LangGraph) clasifica cada mensaje del cliente y lo deriva a uno de tres agentes:

- **preventa** — agente ReAct que consulta el **catálogo real** (Postgres) para buscar productos, precios y ofertas.
- **postventa** — agente ReAct con estado de pedidos, políticas (devoluciones/cambios/garantía) y creación de **reclamos** (Postgres).
- **genérica** — asistente conversacional de la tienda (saluda, responde datos de la tienda, rechaza lo off-topic y el jailbreak).

La conversación tiene **memoria persistente** por cliente (checkpointer de LangGraph sobre Postgres), así que sobrevive a reinicios.

---

## Integrantes y aportes

- **Wil Martínez** — Grupo 7. Implementación completa: router y agentes (preventa / postventa / genérica),
  API FastAPI y control de acceso, memoria persistente y catálogo (Postgres), canal Telegram vía n8n (texto y voz),
  web de chat (Open WebUI) y despliegue en Heroku.

---

## Opción elegida (lo que implementamos)

Del encargo construimos **más de una** opción (se exigía al menos una):

1. **Servicio FastAPI con acceso protegido** — `api/app.py`, con token configurable validado en el servidor.
2. **Canal de atención** — **Telegram** (vía **n8n**, texto y **voz**) y una **web de chat** (Open WebUI, vía un shim OpenAI).
3. **Despliegue verificable (+1 opcional)** — publicado en **Heroku**.

**Problema que resuelve:** atención automática de un ecommerce (consultas de compra, seguimiento de pedidos y reclamos),
derivando cada mensaje al agente adecuado y respondiendo con datos reales del catálogo/pedidos, no respuestas simuladas.

**Qué se reutiliza del trabajo anterior:** la estructura de agentes en `src/{agente}/` (grafo, prompts y tools) y el patrón de
derivación entre agentes especializados.

---

## Arquitectura (rápida)

```
Cliente ──► Canal (Telegram vía n8n / Web Open WebUI / HTTP directo)
                 │
                 ▼
         FastAPI  /chat  (token)
                 │
                 ▼
        Router (LangGraph) ──► preventa / postventa / genérica
                 │                     │
         memoria (Postgres)     catálogo y reclamos (Postgres)
```

- **Modelo:** Google Gemini (`langchain-google-genai`).
- **Memoria:** `PostgresSaver` si hay `DATABASE_URL`; si no, `MemorySaver` (RAM). `GET /health` informa cuál está activa.
- **Catálogo:** vista de solo lectura `catalogo.productos_unicos` (Postgres).

---

## Preparación manual (cuentas y credenciales de prueba)

Todas las claves van solo en `.env` (local) o en los Config Vars del servidor; **nunca** en el repo. Ver `.env.example`.

| Variable | Para qué | Cómo obtenerla |
|---|---|---|
| `GOOGLE_API_KEY` | Modelo Gemini | Google AI Studio → API key |
| `MODELO` | Nombre del modelo | p. ej. `gemini-3.5-flash-lite` |
| `API_TOKEN` | Proteger `/chat` y `/v1` | Lo eliges tú (cadena larga y secreta) |
| `DATABASE_URL` | Memoria + catálogo + reclamos | Cadena de conexión Postgres (base del curso) |
| `TELEGRAM_TOKEN` | Bot de Telegram | @BotFather → nuevo bot |
| `TELEGRAM_SECRET` | Validar el webhook de Telegram | Lo eliges tú |
| `PUBLIC_URL` | Base del webhook (Telegram directo) | URL pública de la app |

El **canal Telegram** usa **n8n** (n8n Cloud): un flujo recibe el mensaje y llama a `/chat`. El JSON del flujo está en
`n8n/flujo_telegram_agente.json`. La **web de chat** usa Open WebUI apuntando al shim `/v1`.

---

## Instalación (local, reproducible)

Requiere **Python 3.12** (ver `.python-version`).

```bash
# 1. Clonar y entrar
git clone <url-del-repo> ecommerce-router
cd ecommerce-router

# 2. Entorno virtual
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Linux/Mac:
# source .venv/bin/activate

# 3. Dependencias
pip install -r requirements.txt

# 4. Configuración
# copia .env.example como .env y rellena los valores reales
cp .env.example .env     # en PowerShell: Copy-Item .env.example .env
```

---

## Comandos: iniciar, probar y detener

### Agente por consola (CLI)
```bash
python main.py router "busco un televisor de 55 pulgadas barato" --saltos
python main.py router "mi pedido 1003 no llega" --hilo demo --saltos
python main.py router "quiero un celular" --diagrama   # imprime el grafo (Mermaid), sin ejecutar
```
- `--saltos`: muestra los nodos y herramientas usados. `--hilo NOMBRE`: elige el hilo de memoria. `--diagrama`: solo dibuja.

### API (FastAPI)
```bash
# Iniciar
uvicorn api.app:app --reload --port 8000
# Detener: Ctrl+C
```
- Documentación interactiva (Swagger): http://localhost:8000/docs
- Salud: http://localhost:8000/health  → `{"ok":true,"modelo":...,"memoria":"postgres|ram"}`

### Probar la API
```bash
# con token (si API_TOKEN está definido)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_TOKEN" \
  --data-raw '{"user_id":"cliente-1","texto":"busco un celular Samsung"}'

# prueba de ruteo end-to-end (6 mensajes)
python scripts/smoke_chat.py            # usa PUBLIC_URL o localhost
```

### Scripts de inspección
```bash
python scripts/ver_catalogo.py "samsung"   # productos por nombre; sin args: conteo por categoría
python scripts/ver_memoria.py              # hilos guardados; con un hilo: su conversación
python scripts/ver_reclamos.py             # reclamos de postventa
```

### Pruebas
```bash
pytest       # pruebas del router (mínimo de aciertos)
```

### Canal Telegram (n8n)
Importar `n8n/flujo_telegram_agente.json` en n8n, configurar la credencial de Telegram (token del bot),
poner la URL de la API en el nodo *Endpoint Agente* y **publicar** el flujo (registra el webhook).
Al activarlo, escribir al bot dispara: Telegram → n8n → `/chat` → respuesta.

### Web de chat (Open WebUI)
Conectar Open WebUI a `http://127.0.0.1:8000/v1` (tipo de API: *Chat Completions*). Si `API_TOKEN` está definido,
usar ese token como *API Key* de la conexión.

---

## Control de acceso (demostrable)

`/chat` y `/v1/*` están protegidos cuando `API_TOKEN` está definido. `/health` queda abierto (monitoreo).

```bash
# Acceso RECHAZADO (sin token o token inválido) → 401
curl -i -X POST http://localhost:8000/chat -H "Content-Type: application/json" \
  --data-raw '{"user_id":"x","texto":"hola"}'

# Acceso PERMITIDO (token correcto) → 200
curl -i -X POST http://localhost:8000/chat -H "Content-Type: application/json" \
  -H "Authorization: Bearer <tu-API_TOKEN>" \
  --data-raw '{"user_id":"x","texto":"hola"}'
```

---

## Evidencias

Las capturas de ejecución local y sus explicaciones están en `evidencias/` (ver `evidencias/EVIDENCIAS.md`).
Cada caso indica entorno/fecha (LOCAL), solicitud, resultado esperado, resultado obtenido y observaciones.

---

## Despliegue en Heroku (+1 opcional)

El proyecto corre en Heroku (`Procfile` + `.python-version` + `requirements.txt`).

```bash
heroku git:remote -a <tu-app>
git push heroku main
# Config Vars (no van en el repo): GOOGLE_API_KEY, MODELO, DATABASE_URL, API_TOKEN, TELEGRAM_TOKEN, TELEGRAM_SECRET, PUBLIC_URL
```
Para proteger `/chat` también en Heroku, definir `API_TOKEN` en Config Vars y hacer que el nodo de n8n envíe el
header `Authorization: Bearer <API_TOKEN>` (credencial *Header Auth* en n8n).

---

## Límites conocidos

- **Clave de Gemini compartida del curso:** si se agota el crédito, `/chat` devuelve **502** limpio y el bot un mensaje de
  "no puedo responder"; no es un bug.
- **Postgres compartida del curso:** los `thread_id` (y los reclamos) pueden colisionar entre estudiantes; para demos usar un hilo propio.
- **Transcripción de voz (Telegram):** depende de que el modelo Gemini acepte audio por el nodo de n8n; si falla, el flujo responde "no pude escuchar tu audio".
- **Pendientes:** canal de WhatsApp y envío de correos (vía MCP) quedaron fuera de esta entrega.
- **Datos de ejemplo:** `data/pedidos.json` y `data/politicas.md` son ficticios; el catálogo es real (base del curso).
