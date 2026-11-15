"""Pydantic schemas for request validation and response serialization."""
from pydantic import BaseModel, ConfigDict


class TaskCreate(BaseModel):
    """Datos para crear una tarea."""

    title: str
    description: str | None = None


class TaskUpdate(BaseModel):
    """Datos opcionales para actualizar una tarea."""

    title: str | None = None
    description: str | None = None
    completed: bool | None = None


class TaskResponse(BaseModel):
    """Tarea devuelta por la API."""

    id: int
    title: str
    description: str | None = None
    completed: bool

    model_config = ConfigDict(from_attributes=True)  # Pydantic v2: leer desde objetos ORM
