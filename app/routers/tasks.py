"""CRUD endpoints for the /tasks resource."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import TaskDB, get_db
from app.models import TaskCreate, TaskResponse, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["Tasks"])


def _get_or_404(task_id: int, db: Session) -> TaskDB:
    """Busca una tarea por ID o lanza 404."""
    task = db.query(TaskDB).filter(TaskDB.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return task


@router.get("/", response_model=list[TaskResponse])  # PEP 585: list[...] sin import
def list_tasks(db: Session = Depends(get_db)) -> list[TaskDB]:
    """Lista todas las tareas."""
    return db.query(TaskDB).all()


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db)) -> TaskDB:
    """Obtiene una tarea por ID."""
    return _get_or_404(task_id, db)


@router.post("/", response_model=TaskResponse, status_code=201)
def create_task(task: TaskCreate, db: Session = Depends(get_db)) -> TaskDB:
    """Crea una nueva tarea."""
    db_task = TaskDB(title=task.title, description=task.description)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


@router.put("/{task_id}", response_model=TaskResponse)
def update_task(task_id: int, updates: TaskUpdate, db: Session = Depends(get_db)) -> TaskDB:
    """Actualiza solo los campos enviados."""
    task = _get_or_404(task_id, db)
    for field, value in updates.model_dump(exclude_unset=True).items():
        setattr(task, field, value)  # aplica solo los campos enviados
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: int, db: Session = Depends(get_db)) -> None:
    """Elimina una tarea."""
    task = _get_or_404(task_id, db)
    db.delete(task)
    db.commit()
