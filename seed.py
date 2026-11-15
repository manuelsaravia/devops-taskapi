"""Pobla la BD con 10 tareas iniciales. Uso: py seed.py [--force]."""
import sys

from app.database import Base, SessionLocal, TaskDB, engine

TASKS: list[dict[str, str | bool]] = [
    # Semana 1 — completadas
    {"title": "Crear estructura FastAPI",
     "description": "Scaffolding del proyecto, requirements.txt y app/", "completed": True},
    {"title": "Implementar CRUD de tareas",
     "description": "GET, POST, PUT, DELETE con SQLAlchemy", "completed": True},
    {"title": "Tests con pytest",
     "description": "11 tests con BD aislada usando dependency override", "completed": True},
    {"title": "Dockerfile multistage",
     "description": "Imagen slim con usuario sin privilegios", "completed": True},
    # Semana 2 — pendientes
    {"title": "Configurar Jenkins",
     "description": "Jenkins LTS con docker-compose en jenkins/", "completed": False},
    {"title": "Escribir Jenkinsfile",
     "description": "Stages Checkout, Test, Build y Push", "completed": False},
    {"title": "Conectar Jenkins con GitHub",
     "description": "Webhook para disparar el pipeline en cada commit", "completed": False},
    # Semana 3 — pendientes
    {"title": "Publicar imagen en registry",
     "description": "Push de la imagen Docker a Docker Hub", "completed": False},
    {"title": "Desplegar en Kubernetes",
     "description": "Deployment y Service con probes en /health", "completed": False},
    {"title": "Monitoreo del servicio",
     "description": "Métricas y alertas básicas", "completed": False},
]


def seed() -> None:
    """Inserta las tareas solo si la tabla está vacía."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(TaskDB).count() > 0:
            print("[!] BD ya tiene datos. Usa --force para reiniciar.")
            return
        for t in TASKS:
            db.add(TaskDB(**t))
        db.commit()
        print(f"[OK] Seed completado: {len(TASKS)} tareas insertadas en tasks.db")
        print("   Prueba la API en: http://localhost:8000/docs")
    finally:
        db.close()


def seed_force() -> None:
    """Borra todas las tareas y vuelve a sembrar."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        db.query(TaskDB).delete()
        db.commit()
        print("[RESET] Base de datos reiniciada.")
    finally:
        db.close()
    seed()


if __name__ == "__main__":
    if "--force" in sys.argv:
        seed_force()
    else:
        seed()
