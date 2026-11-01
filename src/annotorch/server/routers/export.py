from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

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


@router.post("/projects/{pid}/tasks/{tid}/export/zip")
def download_export(pid: str, tid: str, body: ExportIn,
                    svc: ExportService = Depends(export_service)):
    """データセットを一時ディレクトリに作り、<name>/ を1つ含む ZIP として返す。"""
    name = dataset_name(body.name)
    workdir = Path(tempfile.mkdtemp(prefix="annotorch-export-"))
    try:
        svc.export(pid, tid, workdir / name, splits=body.splits, seed=body.seed)
        archive = shutil.make_archive(str(workdir / name), "zip",
                                      root_dir=workdir, base_dir=name)
        size, chunks = open_archive_once(Path(archive), workdir)
    except BaseException:
        shutil.rmtree(workdir, ignore_errors=True)
        raise
    return StreamingResponse(chunks, media_type="application/zip", headers={
        "Content-Length": str(size),
        "Content-Disposition": _attachment(f"{name}.zip"),
    })


def open_archive_once(archive: Path, workdir: Path,
                      chunk_size: int = 1 << 20) -> tuple[int, Iterator[bytes]]:
    """archive を開いて workdir ごと消し、サイズと中身を読み出すイテレータを返す。

    開いたファイルは消した後も読めるので、送信が途中で切れても一時ファイルは残らない。
    消せない OS（Windows）では、読み終わるか途中で閉じられた時点で消す。
    """
    f = open(archive, "rb")  # noqa: SIM115
    size = os.fstat(f.fileno()).st_size
    shutil.rmtree(workdir, ignore_errors=True)

    def chunks() -> Iterator[bytes]:
        try:
            while chunk := f.read(chunk_size):
                yield chunk
        finally:
            f.close()
            shutil.rmtree(workdir, ignore_errors=True)

    return size, chunks()


def _attachment(filename: str) -> str:
    if filename.isascii() and not any(c in filename for c in '"\\'):
        return f'attachment; filename="{filename}"'
    return f"attachment; filename*=utf-8''{quote(filename)}"
