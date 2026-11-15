"""Pruebas de integración de la API (11 tests) con BD en memoria."""

import os
from collections.abc import Generator
from typing import Any

# Evita que importar la app cree tasks.db en disco durante los tests.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest  # noqa: E402
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def override_get_db() -> Generator[Session, None, None]:
    """Sesión de BD en memoria que reemplaza a get_db en los tests."""
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    """Cliente HTTP con una BD limpia para cada test."""
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def _create(client: TestClient, title: str = "Tarea", description: str | None = "Desc") -> dict[str, Any]:
    """Crea una tarea de apoyo y devuelve su JSON."""
    return client.post("/tasks/", json={"title": title, "description": description}).json()


# --- Health (1) ---
def test_health(client: TestClient) -> None:
    """GET /health responde ok."""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# --- Crear (2) ---
def test_create_task(client: TestClient) -> None:
    """Crear tarea con descripción."""
    r = client.post("/tasks/", json={"title": "Comprar pan", "description": "Integral"})
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == "Comprar pan"
    assert data["description"] == "Integral"
    assert data["completed"] is False


def test_create_task_without_description(client: TestClient) -> None:
    """Crear tarea sin descripción."""
    r = client.post("/tasks/", json={"title": "Sin desc"})
    assert r.status_code == 201
    assert r.json()["description"] is None


# --- Listar, obtener, editar, eliminar (5) ---
def test_list_tasks_empty(client: TestClient) -> None:
    """Listar sin tareas devuelve lista vacía."""
    r = client.get("/tasks/")
    assert r.status_code == 200
    assert r.json() == []


def test_list_tasks(client: TestClient) -> None:
    """Listar devuelve las tareas creadas."""
    _create(client, "A")
    _create(client, "B")
    r = client.get("/tasks/")
    assert r.status_code == 200
    assert [t["title"] for t in r.json()] == ["A", "B"]


def test_get_task(client: TestClient) -> None:
    """Obtener una tarea por ID."""
    task = _create(client)
    r = client.get(f"/tasks/{task['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == task["id"]


def test_update_task(client: TestClient) -> None:
    """Editar título y estado."""
    task = _create(client)
    r = client.put(f"/tasks/{task['id']}", json={"title": "Editada", "completed": True})
    assert r.status_code == 200
    assert r.json()["title"] == "Editada"
    assert r.json()["completed"] is True


def test_delete_task(client: TestClient) -> None:
    """Eliminar una tarea y verificar que ya no existe."""
    task = _create(client)
    assert client.delete(f"/tasks/{task['id']}").status_code == 204
    assert client.get("/tasks/").json() == []


# --- 404 (3) ---
def test_get_task_not_found(client: TestClient) -> None:
    """GET de ID inexistente devuelve 404."""
    assert client.get("/tasks/999").status_code == 404


def test_update_task_not_found(client: TestClient) -> None:
    """PUT de ID inexistente devuelve 404."""
    assert client.put("/tasks/999", json={"title": "X"}).status_code == 404


def test_delete_task_not_found(client: TestClient) -> None:
    """DELETE de ID inexistente devuelve 404."""
    assert client.delete("/tasks/999").status_code == 404
