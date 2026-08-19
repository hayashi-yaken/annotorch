from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

from PIL import Image
from pydantic import BaseModel, Field

from ..domain.models import Item, Modality, Project
from ..storage.workspace import Workspace

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}


class SkippedFile(BaseModel):
    source: str
    reason: str


class ImportReport(BaseModel):
    imported: int = 0
    skipped: list[SkippedFile] = Field(default_factory=list)


class ProjectService:
    """プロジェクト管理とアイテム取り込みのユースケース。"""

    def __init__(self, workspace: Workspace):
        self.ws = workspace

    def create(self, name: str, description: str = "") -> Project:
        return self.ws.create_project(name, description)

    def list(self) -> list[Project]:
        return self.ws.list_projects()

    def delete(self, project_id: str) -> None:
        self.ws.delete_project(project_id)

    def list_items(self, project_id: str) -> list[Item]:
        with self.ws.open(project_id) as store:
            return store.list_items(project_id)

    def item_file_path(self, project_id: str, item_id: str) -> Path:
        with self.ws.open(project_id) as store:
            match = [i for i in store.list_items(project_id) if i.id == item_id]
        if not match or match[0].path is None:
            raise LookupError(f"no file for item {item_id}")
        return self.ws.items_dir(project_id) / match[0].path

    def delete_items(self, project_id: str, item_ids: list[str]) -> None:
        """アイテムを削除する。参照中のものが混じっていれば何も削除しない。"""
        with self.ws.open(project_id) as store:
            paths = [i.path for i in store.list_items(project_id)
                     if i.id in set(item_ids) and i.path is not None]
            store.delete_items(item_ids)
        items_dir = self.ws.items_dir(project_id)
        for path in paths:
            (items_dir / path).unlink(missing_ok=True)

    def import_images(self, project_id: str, source_dir: Path) -> ImportReport:
        report = ImportReport()
        items: list[Item] = []
        items_dir = self.ws.items_dir(project_id)
        for path in sorted(p for p in Path(source_dir).rglob("*") if p.is_file()):
            ext = path.suffix.lower()
            if ext not in IMAGE_EXTENSIONS:
                report.skipped.append(
                    SkippedFile(source=str(path), reason=f"unsupported extension {ext!r}")
                )
                continue
            try:
                with Image.open(path) as img:
                    img.verify()
            except Exception as e:
                report.skipped.append(
                    SkippedFile(source=str(path), reason=f"unreadable image: {e}")
                )
                continue
            item = Item(project_id=project_id, modality=Modality.IMAGE,
                        metadata={"source": str(path)})
            item.path = f"{item.id}{ext}"
            shutil.copy2(path, items_dir / item.path)
            items.append(item)
        if items:
            with self.ws.open(project_id) as store:
                store.add_items(items)
        report.imported = len(items)
        return report

    def import_texts_jsonl(self, project_id: str, jsonl_path: Path) -> ImportReport:
        report = ImportReport()
        items: list[Item] = []
        for n, line in enumerate(
            Path(jsonl_path).read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not line.strip():
                continue
            source = f"{jsonl_path}:{n}"
            try:
                record = json.loads(line)
            except json.JSONDecodeError as e:
                report.skipped.append(
                    SkippedFile(source=source, reason=f"invalid JSON: {e}")
                )
                continue
            text = record.pop("text", None) if isinstance(record, dict) else None
            if not isinstance(text, str):
                report.skipped.append(
                    SkippedFile(source=source, reason="missing string 'text' field")
                )
                continue
            items.append(Item(project_id=project_id, modality=Modality.TEXT,
                              text=text, metadata=record))
        if items:
            with self.ws.open(project_id) as store:
                store.add_items(items)
        report.imported = len(items)
        return report

    def import_texts_csv(self, project_id: str, csv_path: Path) -> ImportReport:
        report = ImportReport()
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None or "text" not in reader.fieldnames:
                report.skipped.append(
                    SkippedFile(source=str(csv_path), reason="missing 'text' column")
                )
                return report
            items = []
            for n, row in enumerate(reader, start=1):
                text = row.pop("text")
                if not isinstance(text, str):
                    report.skipped.append(
                        SkippedFile(source=f"{csv_path}:{n}",
                                    reason="missing string 'text' field")
                    )
                    continue
                items.append(Item(project_id=project_id, modality=Modality.TEXT,
                                  text=text, metadata=row))
        if items:
            with self.ws.open(project_id) as store:
                store.add_items(items)
        report.imported = len(items)
        return report
