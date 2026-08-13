from __future__ import annotations

from fastapi import APIRouter, Depends

from ...services.tasks import TaskService
from ..schemas import TaskCreate
from .deps import task_service

router = APIRouter()


@router.post("/projects/{pid}/tasks", status_code=201)
def create_task(pid: str, body: TaskCreate,
                svc: TaskService = Depends(task_service)):
    task, num_units = svc.create_task(pid, body.name, body.presentation,
                                      body.question, body.config)
    return {"task": task, "num_units": num_units}


@router.get("/projects/{pid}/tasks")
def list_tasks(pid: str, svc: TaskService = Depends(task_service)):
    return svc.list_tasks_with_progress(pid)
