"""FastAPI application entry point."""
from fastapi import FastAPI

from app.database import Base, engine
from app.routers import tasks

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="DevOps Task Manager API",
    description="API REST de gestión de tareas — Proyecto Integrador DevOps",
    version="1.1.0",
)

app.include_router(tasks.router)


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    """Endpoint de salud usado por liveness y readiness probes de Kubernetes."""
    return {"status": "ok"}
