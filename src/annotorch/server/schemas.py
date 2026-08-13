from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ..domain.models import Presentation, QuestionType, TaskConfig


class ProjectCreate(BaseModel):
    name: str
    description: str = ""


class FolderImport(BaseModel):
    path: str


class TaskCreate(BaseModel):
    name: str
    presentation: Presentation
    question: QuestionType
    config: TaskConfig = Field(default_factory=TaskConfig)


class AnnotationIn(BaseModel):
    answer: dict[str, Any]


class ExportIn(BaseModel):
    output_dir: str
    splits: dict[str, float] | None = None
    seed: int = 0
