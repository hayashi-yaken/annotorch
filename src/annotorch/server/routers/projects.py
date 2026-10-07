from __future__ import annotations

from fastapi import APIRouter, Depends

from ...services.projects import ProjectService
from ..schemas import ProjectCreate, RenameIn
from .deps import project_service

router = APIRouter()


@router.get("/projects")
def list_projects(svc: ProjectService = Depends(project_service)):
    return svc.list()


@router.post("/projects", status_code=201)
def create_project(body: ProjectCreate,
                   svc: ProjectService = Depends(project_service)):
    return svc.create(body.name, body.description)


@router.patch("/projects/{pid}")
def rename_project(pid: str, body: RenameIn,
                   svc: ProjectService = Depends(project_service)):
    return svc.rename(pid, body.name)


@router.delete("/projects/{pid}")
def delete_project(pid: str, svc: ProjectService = Depends(project_service)):
    svc.delete(pid)
    return {"ok": True}
