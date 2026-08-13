from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ...services.projects import ProjectService
from ..schemas import FolderImport
from .deps import project_service

router = APIRouter()


@router.get("/projects/{pid}/items")
def list_items(pid: str, svc: ProjectService = Depends(project_service)):
    return svc.list_items(pid)


@router.post("/projects/{pid}/items/upload")
async def upload_images(pid: str, files: list[UploadFile],
                        svc: ProjectService = Depends(project_service)):
    with tempfile.TemporaryDirectory() as tmp:
        for f in files:
            name = Path(f.filename or "unnamed").name
            (Path(tmp) / name).write_bytes(await f.read())
        return svc.import_images(pid, Path(tmp))


@router.post("/projects/{pid}/items/upload-texts")
async def upload_texts(pid: str, file: UploadFile,
                       svc: ProjectService = Depends(project_service)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".jsonl", ".csv"}:
        raise HTTPException(400, f"expected .jsonl or .csv (got {suffix!r})")
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / f"upload{suffix}"
        p.write_bytes(await file.read())
        if suffix == ".jsonl":
            return svc.import_texts_jsonl(pid, p)
        return svc.import_texts_csv(pid, p)


@router.post("/projects/{pid}/items/import-folder")
def import_folder(pid: str, body: FolderImport,
                  svc: ProjectService = Depends(project_service)):
    src = Path(body.path)
    if not src.is_dir():
        raise HTTPException(400, f"not a directory: {body.path}")
    return svc.import_images(pid, src)


@router.get("/projects/{pid}/items/{item_id}/file")
def item_file(pid: str, item_id: str,
              svc: ProjectService = Depends(project_service)):
    return FileResponse(svc.item_file_path(pid, item_id))
