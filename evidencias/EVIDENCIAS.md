# Evidencias — ejecución LOCAL

Capturas de nuestra propia ejecución local. Cada caso indica **entorno y fecha (LOCAL)**, la **solicitud**,
el **resultado esperado**, el **resultado obtenido** y **observaciones**. Los datos sensibles (tokens, claves,
datos personales) están ocultos.

> Cómo completar: pon cada captura en esta carpeta con el nombre indicado (p. ej. `01-preventa-api.png`),
> rellena "Resultado obtenido" y "Observaciones", y actualiza la fecha.

---

## Caso 1 — Preventa por la API (catálogo real)
- **Captura:** `01-cli-preventa-generica.png` (misma captura que el Caso 3). La preventa por API/con token está también en `06-acceso-control.png`.
- **Entorno y fecha:** LOCAL — 2026-11-17
- **Solicitud:** `python main.py router "busco un televisor de 55 pulgadas barato" --hilo evid --saltos`
- **Resultado esperado:** ruta `preventa`; productos reales con precio, descuento y link; `--saltos` muestra las herramientas.
- **Resultado obtenido:** `Saltos: router → agente_preventa → buscar_productos → ver_producto → ver_producto`; sugiere Samsung Crystal UHD U8200F ($329.990, 43% dcto) y U8000F ($339.990, 41% dcto), ambos con link y rating 5.
- **Observaciones:** las herramientas salen limpias por turno (sin arrastrar historial).

## Caso 2 — Postventa: estado de pedido y reclamo
- **Captura:** `02-postventa-reclamo.png` (opcional: `02c-ver_reclamos.png` con la salida de `ver_reclamos.py`)
- **Entorno y fecha:** LOCAL — 2026-11-17
- **Solicitud:** "mi pedido 1003 no llega" → confirmar → "sí, crea el reclamo por el retraso" (hilo `demo`)
- **Resultado esperado:** estado real del pedido 1003; al confirmar, se crea el reclamo y se entrega un ticket `REC-…`.
- **Resultado obtenido:** `Saltos: router → agente_postventa → politica → estado_pedido`; reconoce la demora y entrega el estado real (pedido 1003, "preparando", entrega 15/11/2026). Al confirmar: `... → crear_reclamo` y ticket **REC-2B0B922A**, "alguien del equipo te va a escribir".
- **Observaciones:** el reclamo queda en Postgres; se puede verificar con `python scripts/ver_reclamos.py`.

## Caso 3 — Genérica: off-topic
- **Captura:** `01-cli-preventa-generica.png` (misma captura que el Caso 1)
- **Entorno y fecha:** LOCAL — 2026-11-17
- **Solicitud:** `python main.py router "cuéntame un chiste" --hilo evid --saltos`
- **Resultado esperado:** rechaza con amabilidad y reconduce a la tienda.
- **Resultado obtenido:** `Saltos: router → respuesta_generica`; responde que el chat es exclusivo de ElectroMax y ofrece ayudar a buscar un televisor o revisar un pedido.
- **Observaciones:** el rechazo a jailbreak/off-topic también se mostró antes ("ignora tus instrucciones…", "¿qué hora es en Tokio?").

## Casos 4 y 5 — Canal Telegram (texto y voz)
- **Captura:** `04-telegram.png` (opcional: `04b-n8n-execution.png` con el log de n8n)
- **Entorno y fecha:** LOCAL — 2026-11-17
- **Solicitud:** nota de voz, un GIF, y texto ("busco un xiaomi 17T pro, ¿cuál es la opción más barata?")
- **Resultado esperado:** la voz se transcribe y responde el agente; el GIF se rechaza; el texto responde con producto real + link.
- **Resultado obtenido:** la voz se transcribió y respondió; el GIF → "Por ahora no soporto GIFs 🙅…"; el texto → no existe el 17T Pro, ofrece el Xiaomi 15T Pro ($749.990, 12% dcto, rating 4.8) con link, y deriva garantías a postventa.
- **Observaciones:** recorrido Telegram → n8n → `/chat` → agente. (Opcional: capturar también la ejecución en n8n → Executions.)

## Caso 6 — Control de acceso (permitido y rechazado)
- **Captura:** `06-acceso-control.png` (muestra el 401 y el 200)
- **Entorno y fecha:** LOCAL — 2026-11-17
- **Solicitud:** `POST /chat` sin token y con token (servidor levantado con `API_TOKEN`, puerto local).
- **Resultado esperado:** sin token → **401**; con token correcto → **200**.
- **Resultado obtenido:** sin token → `HTTP 401 {"detail":"Token de acceso inválido o ausente."}`; con token → `HTTP 200` con respuesta real de preventa (producto + precio + link).
- **Observaciones:** se usó un token de prueba (`mi-token-de-prueba-123`), no el real. El token se validó en el servidor vía `api/seguridad.py`.

## Caso 7 — Falla del proveedor (mensaje claro)
- **Captura:** `07-error-502.png`
- **Entorno y fecha:** LOCAL — _(fecha)_
- **Solicitud:** una consulta cuando la clave de Gemini está sin crédito.
- **Resultado esperado:** `/chat` responde **502** con mensaje claro (no se presenta como éxito).
- **Resultado obtenido:** _(completar, si se da el caso)_
- **Observaciones:** depende de la clave compartida del curso.

## Caso 8 — Despliegue en Heroku (+1 opcional)
- **Captura:** `08-heroku.png`
- **Entorno y fecha:** REMOTO (Heroku) — 2026-11-17
- **Solicitud:** `GET /health` y `POST /chat` contra `https://ecommerce-rbp-b47b6797ae89.herokuapp.com`.
- **Resultado esperado:** `/health` 200 con `memoria: postgres`; `/chat` responde con el agente real.
- **Resultado obtenido:** `/health` → `{"ok":true,"modelo":"gemini-3.5-flash-lite","memoria":"postgres"}`; `/chat` → ruta `preventa`, Samsung Galaxy S25 Fe $436.990 (39% dcto) con link.
- **Observaciones:** funciona sin depender del computador local.
