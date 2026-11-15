"""Integration tests for the Task Manager API."""
import os
from collections.abc import Generator

# Evita que importar la app cree tasks.db en disco durante los tests.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402

# BD en memoria: sin archivos residuales, conexiones compartidas via StaticPool
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db() -> Generator[Session, None, None]:
    """Sesión de BD en memoria que reemplaza a get_db."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)  # se ejecuta en cada test automáticamente
def setup_db() -> Generator[None, None, None]:
    """Crea las tablas antes de cada test y las borra después."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


client = TestClient(app)


def _crear(title: str = "Tarea", description: str | None = "Desc") -> dict:
    """Crea una tarea de apoyo y devuelve su JSON."""
    return client.post("/tasks/", json={"title": title, "description": description}).json()


def test_health_check() -> None:
    """GET /health responde ok."""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_create_task() -> None:
    """Crear tarea con descripción."""
    r = client.post("/tasks/", json={"title": "Mi tarea", "description": "Desc"})
    assert r.status_code == 201
    assert r.json()["title"] == "Mi tarea"
    assert r.json()["completed"] is False


def test_create_task_sin_descripcion() -> None:
    """Crear tarea sin descripción."""
    r = client.post("/tasks/", json={"title": "Sin desc"})
    assert r.status_code == 201
    assert r.json()["description"] is None


def test_listar_tareas_vacia() -> None:
    """Listar sin tareas devuelve lista vacía."""
    r = client.get("/tasks/")
    assert r.status_code == 200
    assert r.json() == []


def test_listar_tareas() -> None:
    """Listar devuelve las tareas creadas."""
    _crear("A")
    _crear("B")
    r = client.get("/tasks/")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_get_task_existente() -> None:
    """Obtener tarea existente por ID."""
    task = _crear()
    r = client.get(f"/tasks/{task['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == task["id"]


def test_get_task_no_existente() -> None:
    """GET de ID inexistente devuelve 404."""
    assert client.get("/tasks/999").status_code == 404


def test_update_task() -> None:
    """Actualizar título y estado."""
    task = _crear()
    r = client.put(f"/tasks/{task['id']}", json={"title": "Editada", "completed": True})
    assert r.status_code == 200
    assert r.json()["title"] == "Editada"
    assert r.json()["completed"] is True
    assert r.json()["description"] == "Desc"  # campo no enviado se conserva


def test_update_task_no_existente() -> None:
    """PUT de ID inexistente devuelve 404."""
    assert client.put("/tasks/999", json={"title": "X"}).status_code == 404


def test_eliminar_tarea() -> None:
    """Eliminar tarea y verificar que ya no existe."""
    task = _crear()
    assert client.delete(f"/tasks/{task['id']}").status_code == 204
    assert client.get(f"/tasks/{task['id']}").status_code == 404


def test_eliminar_tarea_no_existente() -> None:
    """DELETE de ID inexistente devuelve 404."""
    assert client.delete("/tasks/999").status_code == 404
