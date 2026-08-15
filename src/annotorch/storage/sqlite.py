from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from ..domain.models import (
    Annotation,
    Annotator,
    Item,
    Modality,
    Presentation,
    Project,
    QuestionType,
    Task,
    TaskConfig,
    Unit,
)

SCHEMA_VERSION = "1"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS items (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    modality TEXT NOT NULL,
    path TEXT,
    text TEXT,
    metadata TEXT NOT NULL DEFAULT '{}',
    seq INTEGER
);
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    name TEXT NOT NULL,
    presentation TEXT NOT NULL,
    question TEXT NOT NULL,
    config TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS units (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES tasks(id),
    position INTEGER NOT NULL,
    item_ids TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS annotators (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS annotations (
    id TEXT PRIMARY KEY,
    unit_id TEXT NOT NULL REFERENCES units(id),
    annotator_id TEXT NOT NULL REFERENCES annotators(id),
    answer TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (unit_id, annotator_id)
);
"""


class SqliteStore:
    """ProjectStore の SQLite 実装。1ファイル = 1プロジェクト。"""

    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        with self.conn:
            self.conn.executescript(_SCHEMA)
            self.conn.execute(
                "INSERT OR IGNORE INTO meta (key, value) VALUES ('schema_version', ?)",
                (SCHEMA_VERSION,),
            )
        row = self.conn.execute(
            "SELECT value FROM meta WHERE key = 'schema_version'"
        ).fetchone()
        if row is not None and row["value"] != SCHEMA_VERSION:
            self.conn.close()
            raise RuntimeError(
                f"unsupported schema_version {row['value']} (expected {SCHEMA_VERSION})"
            )

    def close(self) -> None:
        self.conn.close()

    # -- project ------------------------------------------------------------

    def add_project(self, p: Project) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO projects (id, name, description, created_at) VALUES (?, ?, ?, ?)",
                (p.id, p.name, p.description, p.created_at.isoformat()),
            )

    def get_project(self) -> Project:
        row = self.conn.execute("SELECT * FROM projects LIMIT 1").fetchone()
        if row is None:
            raise LookupError(f"no project in {self.db_path}")
        return Project(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    # -- items --------------------------------------------------------------

    def add_items(self, items: list[Item]) -> None:
        base = self.conn.execute("SELECT COALESCE(MAX(seq), -1) FROM items").fetchone()[0]
        with self.conn:
            self.conn.executemany(
                "INSERT INTO items (id, project_id, modality, path, text, metadata, seq)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    (i.id, i.project_id, i.modality.value, i.path, i.text,
                     json.dumps(i.metadata), base + 1 + n)
                    for n, i in enumerate(items)
                ],
            )

    def list_items(self, project_id: str) -> list[Item]:
        rows = self.conn.execute(
            "SELECT * FROM items WHERE project_id = ? ORDER BY seq", (project_id,)
        ).fetchall()
        return [
            Item(
                id=r["id"],
                project_id=r["project_id"],
                modality=Modality(r["modality"]),
                path=r["path"],
                text=r["text"],
                metadata=json.loads(r["metadata"]),
            )
            for r in rows
        ]

    # -- tasks --------------------------------------------------------------

    def add_task(self, t: Task) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO tasks (id, project_id, name, presentation, question, config)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (t.id, t.project_id, t.name, t.presentation.value, t.question.value,
                 t.config.model_dump_json()),
            )

    def _row_to_task(self, r: sqlite3.Row) -> Task:
        return Task(
            id=r["id"],
            project_id=r["project_id"],
            name=r["name"],
            presentation=Presentation(r["presentation"]),
            question=QuestionType(r["question"]),
            config=TaskConfig.model_validate_json(r["config"]),
        )

    def get_task(self, task_id: str) -> Task:
        row = self.conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            raise LookupError(f"no task {task_id}")
        return self._row_to_task(row)

    def list_tasks(self, project_id: str) -> list[Task]:
        rows = self.conn.execute(
            "SELECT * FROM tasks WHERE project_id = ? ORDER BY rowid", (project_id,)
        ).fetchall()
        return [self._row_to_task(r) for r in rows]

    def delete_task(self, task_id: str) -> None:
        # 外部キーの下から順に消す（annotations -> units -> task）。
        # 1トランザクションなので、途中で失敗すれば何も消えない。
        self.get_task(task_id)  # 未知の task は LookupError
        with self.conn:
            self.conn.execute(
                "DELETE FROM annotations WHERE unit_id IN"
                " (SELECT id FROM units WHERE task_id = ?)",
                (task_id,),
            )
            self.conn.execute("DELETE FROM units WHERE task_id = ?", (task_id,))
            self.conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

    # -- units --------------------------------------------------------------

    def add_units(self, units: list[Unit]) -> None:
        with self.conn:
            self.conn.executemany(
                "INSERT INTO units (id, task_id, position, item_ids) VALUES (?, ?, ?, ?)",
                [(u.id, u.task_id, u.position, json.dumps(u.item_ids)) for u in units],
            )

    def list_units(self, task_id: str) -> list[Unit]:
        rows = self.conn.execute(
            "SELECT * FROM units WHERE task_id = ? ORDER BY position", (task_id,)
        ).fetchall()
        return [
            Unit(id=r["id"], task_id=r["task_id"], item_ids=json.loads(r["item_ids"]),
                 position=r["position"])
            for r in rows
        ]

    # -- annotators / annotations --------------------------------------------

    def get_default_annotator(self) -> Annotator:
        with self.conn:
            self.conn.execute(
                "INSERT OR IGNORE INTO annotators (id, name) VALUES ('default', 'default')"
            )
        row = self.conn.execute(
            "SELECT * FROM annotators WHERE id = 'default'"
        ).fetchone()
        return Annotator(id=row["id"], name=row["name"])

    def save_annotation(self, a: Annotation) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO annotations (id, unit_id, annotator_id, answer, created_at)"
                " VALUES (?, ?, ?, ?, ?)"
                " ON CONFLICT (unit_id, annotator_id) DO UPDATE SET"
                "   answer = excluded.answer, created_at = excluded.created_at",
                (a.id, a.unit_id, a.annotator_id, json.dumps(a.answer),
                 a.created_at.isoformat()),
            )

    def list_annotations_for_task(self, task_id: str) -> list[Annotation]:
        rows = self.conn.execute(
            "SELECT a.* FROM annotations a JOIN units u ON a.unit_id = u.id"
            " WHERE u.task_id = ? ORDER BY u.position",
            (task_id,),
        ).fetchall()
        return [
            Annotation(
                id=r["id"],
                unit_id=r["unit_id"],
                annotator_id=r["annotator_id"],
                answer=json.loads(r["answer"]),
                created_at=datetime.fromisoformat(r["created_at"]),
            )
            for r in rows
        ]
