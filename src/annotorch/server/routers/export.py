from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends

from ...services.exports import ExportService
from ..paths import dataset_name
from ..schemas import ExportIn
from .deps import export_root, export_service

router = APIRouter()


@router.post("/projects/{pid}/tasks/{tid}/export")
def export_task(pid: str, tid: str, body: ExportIn,
                root: Path = Depends(export_root),
                svc: ExportService = Depends(export_service)):
    out = root.resolve() / dataset_name(body.name)
    return svc.export(pid, tid, out, splits=body.splits, seed=body.seed)
