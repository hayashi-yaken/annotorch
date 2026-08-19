from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


def _new_id() -> str:
    return uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ItemsInUseError(Exception):
    """タスクの unit から参照されているアイテムを削除しようとした。"""

    def __init__(self, item_ids: list[str], task_names: list[str]):
        self.item_ids = item_ids
        self.task_names = task_names
        super().__init__(
            f"{len(item_ids)} item(s) are still used by task(s): "
            + ", ".join(task_names)
        )


class Modality(StrEnum):
    IMAGE = "image"
    TEXT = "text"


class Presentation(StrEnum):
    SINGLE = "single"
    PAIR = "pair"
    GROUP = "group"


class QuestionType(StrEnum):
    HARD_LABEL = "hard_label"
    SOFT_LABEL = "soft_label"
    PREFERENCE = "preference"
    SIMILARITY = "similarity"
    RANKING = "ranking"
    GROUPING = "grouping"


VALID_QUESTIONS: dict[Presentation, set[QuestionType]] = {
    Presentation.SINGLE: {QuestionType.HARD_LABEL, QuestionType.SOFT_LABEL},
    Presentation.PAIR: {QuestionType.PREFERENCE, QuestionType.SIMILARITY},
    Presentation.GROUP: {QuestionType.RANKING, QuestionType.GROUPING},
}

LABEL_QUESTIONS = {QuestionType.HARD_LABEL, QuestionType.SOFT_LABEL}


class Project(BaseModel):
    id: str = Field(default_factory=_new_id)
    name: str
    description: str = ""
    created_at: datetime = Field(default_factory=_now)


class Item(BaseModel):
    id: str = Field(default_factory=_new_id)
    project_id: str
    modality: Modality
    path: str | None = None  # image: items ディレクトリ内の相対パス
    text: str | None = None  # text: 本文そのもの
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskConfig(BaseModel):
    labels: list[str] | None = None
    similarity_mode: Literal["binary", "continuous"] = "continuous"
    group_size: int | None = None
    num_units: int | None = None
    seed: int = 0
    pairing: Literal["random", "anchor"] = "random"
    anchor_item_ids: list[str] | None = None


class Task(BaseModel):
    id: str = Field(default_factory=_new_id)
    project_id: str
    name: str
    presentation: Presentation
    question: QuestionType
    config: TaskConfig = Field(default_factory=TaskConfig)

    @model_validator(mode="after")
    def _check(self) -> "Task":
        if self.question not in VALID_QUESTIONS[self.presentation]:
            raise ValueError(
                f"question {self.question} is not valid for presentation {self.presentation}"
            )
        if self.question in LABEL_QUESTIONS and not self.config.labels:
            raise ValueError(f"question {self.question} requires config.labels")
        if self.config.pairing == "anchor":
            if self.presentation != Presentation.PAIR:
                raise ValueError(
                    f"anchor pairing requires presentation {Presentation.PAIR}"
                    f" (got {self.presentation})"
                )
            anchors = self.config.anchor_item_ids
            if not anchors:
                raise ValueError("anchor pairing requires config.anchor_item_ids")
            if len(set(anchors)) != len(anchors):
                dups = [id for id, count in Counter(anchors).items() if count > 1]
                raise ValueError(f"config.anchor_item_ids must not contain duplicates (found: {dups})")
        elif self.config.anchor_item_ids:
            raise ValueError(
                "config.anchor_item_ids requires config.pairing='anchor'"
            )
        return self


class Unit(BaseModel):
    id: str = Field(default_factory=_new_id)
    task_id: str
    item_ids: list[str]
    position: int


class Annotator(BaseModel):
    id: str = Field(default_factory=_new_id)
    name: str


class Annotation(BaseModel):
    id: str = Field(default_factory=_new_id)
    unit_id: str
    annotator_id: str
    answer: dict[str, Any]
    created_at: datetime = Field(default_factory=_now)
