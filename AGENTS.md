# AGENTS.md

Reglas del proyecto para cualquier persona o agente de IA que trabaje en este repositorio.

## Estructura de los agentes

- Cada agente vive en `src/{nombre_agente}/` y contiene:
  - `graph.py`: definición del grafo de LangGraph (nodos, aristas y estado).
  - `prompts.py`: los prompts. **Cada nodo tiene su propio prompt** aquí.
  - `tools.py`: las herramientas que usa el agente.
- **Nada de reglas ni prompts dentro de `graph.py`**: toda instrucción para el modelo va en `prompts.py`.

## Ejecución desde la raíz

```bash
python main.py {nombre_agente} "mensaje"
```

Flags:

- `--saltos`: además de la respuesta, imprime los nodos por los que pasó el grafo.
- `--diagrama`: imprime el diagrama Mermaid del grafo **sin ejecutarlo**.

## API

- La API va en `api/app.py` (FastAPI).
- Se levanta con:

```bash
uvicorn api.app:app --reload --port 8000
```

## Scripts y pruebas

- Los scripts sueltos van en `scripts/`.
- Las pruebas van en `tests/` y se ejecutan con `pytest`.

## Despliegue en Heroku

- `Procfile` con:

  ```
  web: uvicorn api.app:app --host 0.0.0.0 --port $PORT
  ```

- `.python-version` con `3.12`.
- `requirements.txt` **siempre actualizado** (tras instalar algo: `pip freeze > requirements.txt`).

## Configuración y secretos

- Las variables de entorno se documentan en `.env.example`; los valores reales van solo en `.env`.
- **Nunca** poner valores reales (claves, tokens) en el código.
- `.gitignore` debe incluir `.env`, `.venv`, `__pycache__` y `.langgraph_api`.
