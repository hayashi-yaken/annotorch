from __future__ import annotations

import shutil
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from ..domain.models import Project
from .repository import ProjectStore
from .sqlite import SqliteStore


class Workspace:
    """root/projects/<project_id>/{project.db, items/} のレイアウトを管理する。"""

    def __init__(self, root: Path | str):
        self.root = Path(root)

    def _project_dir(self, project_id: str) -> Path:
        return self.root / "projects" / project_id

    def create_project(self, name: str, description: str = "") -> Project:
        project = Project(name=name, description=description)
        store = SqliteStore(self._project_dir(project.id) / "project.db")
        try:
            store.add_project(project)
        finally:
            store.close()
        self.items_dir(project.id)
        return project

    def list_projects(self) -> list[Project]:
        projects_dir = self.root / "projects"
        if not projects_dir.is_dir():
            return []
        out: list[Project] = []
        for db in sorted(projects_dir.glob("*/project.db")):
            store = SqliteStore(db)
            try:
                out.append(store.get_project())
            finally:
                store.close()
        return out

    def delete_project(self, project_id: str) -> None:
        d = self._project_dir(project_id)
        if not d.is_dir():
            raise LookupError(f"no project {project_id} under {self.root}")
        shutil.rmtree(d)

    def storage(self, project_id: str) -> SqliteStore:
        db = self._project_dir(project_id) / "project.db"
        if not db.exists():
            raise LookupError(f"no project {project_id} under {self.root}")
        return SqliteStore(db)

    @contextmanager
    def open(self, project_id: str) -> Iterator[ProjectStore]:
        store = self.storage(project_id)
        try:
            yield store
        finally:
            store.close()

    def items_dir(self, project_id: str) -> Path:
        d = self._project_dir(project_id) / "items"
        d.mkdir(parents=True, exist_ok=True)
        return d
