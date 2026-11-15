"""Pobla la base de datos con 10 tareas de ejemplo.

Uso:
    py seed.py           # solo si la tabla está vacía
    py seed.py --force   # borra las tareas existentes y vuelve a sembrar
"""

import argparse

from sqlalchemy import delete, func, select

from app.database import Base, SessionLocal, engine
from app.models import TaskDB

SAMPLE_TASKS: list[tuple[str, str | None, bool]] = [
    ("Configurar repositorio Git", "Crear repo y primer commit", True),
    ("Crear entorno virtual", "py -m venv .venv", True),
    ("Instalar dependencias", "pip install -r requirements.txt", True),
    ("Definir modelo TaskDB", "SQLAlchemy 2.0", False),
    ("Crear esquemas Pydantic", None, False),
    ("Implementar endpoints CRUD", "GET, POST, PUT, DELETE", False),
    ("Escribir tests", "11 pruebas con pytest", False),
    ("Crear Dockerfile", "Multietapa con python:3.12-slim", False),
    ("Configurar docker-compose", "Con hot-reload", False),
    ("Documentar el proyecto", None, False),
]


def seed(force: bool = False) -> None:
    """Inserta las tareas de ejemplo."""
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        count = db.scalar(select(func.count()).select_from(TaskDB)) or 0
        if count and not force:
            print(f"La BD ya tiene {count} tareas. Use --force para reemplazarlas.")
            return
        if force:
            db.execute(delete(TaskDB))
        db.add_all(
            TaskDB(title=t, description=d, completed=c) for t, d, c in SAMPLE_TASKS
        )
        db.commit()
        print(f"Se insertaron {len(SAMPLE_TASKS)} tareas.")


def main() -> None:
    """Lee argumentos de la línea de comandos y ejecuta el seed."""
    parser = argparse.ArgumentParser(description="Poblar la BD con tareas de ejemplo")
    parser.add_argument("--force", action="store_true", help="Reemplazar tareas existentes")
    seed(force=parser.parse_args().force)


if __name__ == "__main__":
    main()
