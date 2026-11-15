"""Endpoints CRUD para las tareas."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import TaskCreate, TaskDB, TaskResponse, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _get_or_404(task_id: int, db: Session) -> TaskDB:
    """Busca una tarea por ID o lanza 404."""
    task = db.get(TaskDB, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/", response_model=list[TaskResponse])
def list_tasks(db: Session = Depends(get_db)) -> list[TaskDB]:
    """Lista todas las tareas."""
    return list(db.scalars(select(TaskDB).order_by(TaskDB.id)).all())


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)) -> TaskDB:
    """Crea una nueva tarea."""
    task = TaskDB(**payload.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db)) -> TaskDB:
    """Obtiene una tarea por ID."""
    return _get_or_404(task_id, db)


@router.put("/{task_id}", response_model=TaskResponse)
def update_task(task_id: int, payload: TaskUpdate, db: Session = Depends(get_db)) -> TaskDB:
    """Actualiza solo los campos enviados de una tarea."""
    task = _get_or_404(task_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: Session = Depends(get_db)) -> Response:
    """Elimina una tarea."""
    task = _get_or_404(task_id, db)
    db.delete(task)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
