from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ValidationError

from .models import QuestionType, Task, Unit

SUM_TOLERANCE = 1e-3


class AnswerValidationError(ValueError):
    pass


class HardLabelAnswer(BaseModel):
    label: str


class SoftLabelAnswer(BaseModel):
    dist: dict[str, float]


class PreferenceAnswer(BaseModel):
    # 1 = unit.item_ids の1番目の勝ち, -1 = 2番目の勝ち, 0 = tie, None = skip
    winner: Literal[1, -1, 0] | None


class SimilarityAnswer(BaseModel):
    score: float | None = None
    same: bool | None = None


class RankingAnswer(BaseModel):
    order: list[str]


class GroupingAnswer(BaseModel):
    groups: list[list[str]]


def _parse(model_cls: type[BaseModel], answer: dict[str, Any]) -> BaseModel:
    try:
        return model_cls.model_validate(answer, strict=False)
    except ValidationError as e:
        raise AnswerValidationError(str(e)) from e


def validate_answer(task: Task, unit: Unit, answer: dict[str, Any]) -> dict[str, Any]:
    """回答dictをタスク定義とUnitに対して検証し、正規化済みdictを返す。"""
    q = task.question

    if q == QuestionType.HARD_LABEL:
        parsed = _parse(HardLabelAnswer, answer)
        if parsed.label not in (task.config.labels or []):
            raise AnswerValidationError(f"unknown label: {parsed.label!r}")
        return {"label": parsed.label}

    if q == QuestionType.SOFT_LABEL:
        parsed = _parse(SoftLabelAnswer, answer)
        labels = set(task.config.labels or [])
        unknown = set(parsed.dist) - labels
        if unknown:
            raise AnswerValidationError(f"unknown classes in dist: {sorted(unknown)}")
        if any(v < 0 for v in parsed.dist.values()):
            raise AnswerValidationError("dist values must be non-negative")
        total = sum(parsed.dist.values())
        if abs(total - 1.0) > SUM_TOLERANCE:
            raise AnswerValidationError(f"dist must sum to 1 (got {total})")
        return {"dist": {k: v / total for k, v in parsed.dist.items()}}

    if q == QuestionType.PREFERENCE:
        parsed = _parse(PreferenceAnswer, answer)
        return {"winner": parsed.winner}

    if q == QuestionType.SIMILARITY:
        parsed = _parse(SimilarityAnswer, answer)
        if task.config.similarity_mode == "binary":
            if parsed.same is None or parsed.score is not None:
                raise AnswerValidationError("binary similarity requires {'same': bool}")
            return {"same": parsed.same}
        if parsed.score is None or parsed.same is not None:
            raise AnswerValidationError("continuous similarity requires {'score': float}")
        if not 0.0 <= parsed.score <= 1.0:
            raise AnswerValidationError(f"score must be in [0, 1] (got {parsed.score})")
        return {"score": parsed.score}

    if q == QuestionType.RANKING:
        parsed = _parse(RankingAnswer, answer)
        if sorted(parsed.order) != sorted(unit.item_ids):
            raise AnswerValidationError("order must be a permutation of the unit's items")
        return {"order": parsed.order}

    if q == QuestionType.GROUPING:
        parsed = _parse(GroupingAnswer, answer)
        if any(len(g) == 0 for g in parsed.groups):
            raise AnswerValidationError("groups must be non-empty")
        flat = [i for g in parsed.groups for i in g]
        if sorted(flat) != sorted(unit.item_ids):
            raise AnswerValidationError(
                "groups must partition the unit's items (no overlap, no missing)"
            )
        return {"groups": parsed.groups}

    raise AnswerValidationError(f"unsupported question type: {q}")
