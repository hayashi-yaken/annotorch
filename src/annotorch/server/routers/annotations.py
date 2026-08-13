from __future__ import annotations

from fastapi import APIRouter, Depends

from ...services.tasks import TaskService
from ..schemas import AnnotationIn
from .deps import task_service

router = APIRouter()


@router.get("/projects/{pid}/tasks/{tid}/units")
def list_units(pid: str, tid: str, svc: TaskService = Depends(task_service)):
    return svc.list_units(pid, tid)


@router.put("/projects/{pid}/tasks/{tid}/units/{uid}/annotation")
def save_annotation(pid: str, tid: str, uid: str, body: AnnotationIn,
                    svc: TaskService = Depends(task_service)):
    answer = svc.save_answer(pid, tid, uid, body.answer)
    return {"unit_id": uid, "answer": answer}
