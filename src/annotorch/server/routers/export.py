from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends

from ...services.exports import ExportService
from ..schemas import ExportIn
from .deps import export_service

router = APIRouter()


@router.post("/projects/{pid}/tasks/{tid}/export")
def export_task(pid: str, tid: str, body: ExportIn,
                svc: ExportService = Depends(export_service)):
    return svc.export(pid, tid, Path(body.output_dir),
                      splits=body.splits, seed=body.seed)
