# DevOps Task Manager API

API REST de gestión de tareas — Proyecto Integrador DevOps, Semana 1.

**Stack:** FastAPI · SQLAlchemy 2.0 · SQLite · Pydantic v2 · pytest · Docker

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Liveness probe |
| GET | `/tasks/` | Listar tareas |
| POST | `/tasks/` | Crear tarea |
| GET | `/tasks/{id}` | Obtener tarea |
| PUT | `/tasks/{id}` | Actualizar tarea (parcial) |
| DELETE | `/tasks/{id}` | Eliminar tarea |

Documentación interactiva: http://localhost:8000/docs

## Uso local (Windows)

```bash
py -m pip install -r requirements.txt
py -m pytest tests/ -v          # 11 tests
py seed.py                      # 10 tareas de ejemplo (--force para reiniciar)
py -m uvicorn app.main:app --reload
```

## Docker

```bash
docker build -t devops-task-api:local .
docker run -p 8000:8000 devops-task-api:local

# Desarrollo con hot-reload
docker compose up --build
docker compose down
```

> Nota: `requirements.txt` usa las versiones de la guía para Python < 3.13 (imagen Docker 3.12)
> y versiones compatibles más recientes para Python 3.13+, donde SQLAlchemy 2.0.40 y
> Pydantic 2.10.3 no funcionan.
