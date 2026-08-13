from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ValidationError

from ..domain.answers import validate_answer
from ..domain.models import (
    Annotation,
    Item,
    Presentation,
    QuestionType,
    Task,
    TaskConfig,
)
from ..domain.units import generate_units
from ..storage.workspace import Workspace


class TaskWithProgress(Task):
    total_units: int
    answered_units: int


class UnitDetail(BaseModel):
    id: str
    position: int
    items: list[Item]
    answer: dict[str, Any] | None


class TaskService:
    """タスク定義・Unit提示・回答保存のユースケース。"""

    def __init__(self, workspace: Workspace):
        self.ws = workspace

    def create_task(self, project_id: str, name: str, presentation: Presentation,
                    question: QuestionType, config: TaskConfig) -> tuple[Task, int]:
        try:
            task = Task(project_id=project_id, name=name, presentation=presentation,
                        question=question, config=config)
        except ValidationError as e:
            raise ValueError(str(e)) from e
        with self.ws.open(project_id) as store:
            item_ids = [i.id for i in store.list_items(project_id)]
            units = generate_units(task, item_ids)  # 設定不正は ValueError
            store.add_task(task)
            store.add_units(units)
        return task, len(units)

    def list_tasks_with_progress(self, project_id: str) -> list[TaskWithProgress]:
        with self.ws.open(project_id) as store:
            out = []
            for task in store.list_tasks(project_id):
                units = store.list_units(task.id)
                anns = store.list_annotations_for_task(task.id)
                out.append(TaskWithProgress(
                    **task.model_dump(),
                    total_units=len(units),
                    answered_units=len({a.unit_id for a in anns}),
                ))
            return out

    def list_units(self, project_id: str, task_id: str) -> list[UnitDetail]:
        with self.ws.open(project_id) as store:
            store.get_task(task_id)  # 未知の task は LookupError
            items = {i.id: i for i in store.list_items(project_id)}
            answers = {a.unit_id: a.answer
                       for a in store.list_annotations_for_task(task_id)}
            return [
                UnitDetail(id=u.id, position=u.position,
                           items=[items[i] for i in u.item_ids],
                           answer=answers.get(u.id))
                for u in store.list_units(task_id)
            ]

    def save_answer(self, project_id: str, task_id: str, unit_id: str,
                    answer: dict[str, Any]) -> dict[str, Any]:
        with self.ws.open(project_id) as store:
            task = store.get_task(task_id)
            unit = next((u for u in store.list_units(task_id) if u.id == unit_id), None)
            if unit is None:
                raise LookupError(f"no unit {unit_id}")
            validated = validate_answer(task, unit, answer)
            annotator = store.get_default_annotator()
            store.save_annotation(Annotation(unit_id=unit_id,
                                             annotator_id=annotator.id,
                                             answer=validated))
            return validated
