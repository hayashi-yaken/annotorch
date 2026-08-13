import pytest

from annotorch.domain.answers import AnswerValidationError, validate_answer
from annotorch.domain.models import Presentation, QuestionType, Task, TaskConfig, Unit


def make_task(presentation, question, **config):
    return Task(
        project_id="p",
        name="t",
        presentation=presentation,
        question=question,
        config=TaskConfig(**config),
    )


def make_unit(task, item_ids):
    return Unit(task_id=task.id, item_ids=item_ids, position=0)


class TestHardLabel:
    def setup_method(self):
        self.task = make_task(
            Presentation.SINGLE, QuestionType.HARD_LABEL, labels=["cat", "dog"]
        )
        self.unit = make_unit(self.task, ["i1"])

    def test_valid(self):
        out = validate_answer(self.task, self.unit, {"label": "cat"})
        assert out == {"label": "cat"}

    def test_unknown_label(self):
        with pytest.raises(AnswerValidationError):
            validate_answer(self.task, self.unit, {"label": "bird"})


class TestSoftLabel:
    def setup_method(self):
        self.task = make_task(
            Presentation.SINGLE, QuestionType.SOFT_LABEL, labels=["cat", "dog"]
        )
        self.unit = make_unit(self.task, ["i1"])

    def test_valid_and_renormalized(self):
        out = validate_answer(self.task, self.unit, {"dist": {"cat": 0.7, "dog": 0.3001}})
        assert abs(sum(out["dist"].values()) - 1.0) < 1e-9

    def test_sum_far_from_one(self):
        with pytest.raises(AnswerValidationError):
            validate_answer(self.task, self.unit, {"dist": {"cat": 0.5, "dog": 0.3}})

    def test_unknown_class(self):
        with pytest.raises(AnswerValidationError):
            validate_answer(self.task, self.unit, {"dist": {"bird": 1.0}})


class TestPreference:
    def setup_method(self):
        self.task = make_task(Presentation.PAIR, QuestionType.PREFERENCE, num_units=1)
        self.unit = make_unit(self.task, ["i1", "i2"])

    def test_valid(self):
        assert validate_answer(self.task, self.unit, {"winner": 1}) == {"winner": 1}
        assert validate_answer(self.task, self.unit, {"winner": -1}) == {"winner": -1}
        assert validate_answer(self.task, self.unit, {"winner": 0}) == {"winner": 0}
        assert validate_answer(self.task, self.unit, {"winner": None}) == {"winner": None}

    def test_invalid_winner(self):
        with pytest.raises(AnswerValidationError):
            validate_answer(self.task, self.unit, {"winner": 2})


class TestSimilarity:
    def test_continuous_valid(self):
        task = make_task(
            Presentation.PAIR, QuestionType.SIMILARITY, similarity_mode="continuous"
        )
        unit = make_unit(task, ["i1", "i2"])
        assert validate_answer(task, unit, {"score": 0.8}) == {"score": 0.8}

    def test_continuous_out_of_range(self):
        task = make_task(
            Presentation.PAIR, QuestionType.SIMILARITY, similarity_mode="continuous"
        )
        unit = make_unit(task, ["i1", "i2"])
        with pytest.raises(AnswerValidationError):
            validate_answer(task, unit, {"score": 1.5})

    def test_binary_requires_same(self):
        task = make_task(
            Presentation.PAIR, QuestionType.SIMILARITY, similarity_mode="binary"
        )
        unit = make_unit(task, ["i1", "i2"])
        assert validate_answer(task, unit, {"same": True}) == {"same": True}
        with pytest.raises(AnswerValidationError):
            validate_answer(task, unit, {"score": 0.5})


class TestRanking:
    def setup_method(self):
        self.task = make_task(
            Presentation.GROUP, QuestionType.RANKING, group_size=3, num_units=1
        )
        self.unit = make_unit(self.task, ["i1", "i2", "i3"])

    def test_valid_permutation(self):
        out = validate_answer(self.task, self.unit, {"order": ["i3", "i1", "i2"]})
        assert out == {"order": ["i3", "i1", "i2"]}

    def test_not_a_permutation(self):
        with pytest.raises(AnswerValidationError):
            validate_answer(self.task, self.unit, {"order": ["i1", "i1", "i2"]})
        with pytest.raises(AnswerValidationError):
            validate_answer(self.task, self.unit, {"order": ["i1", "i2"]})


class TestGrouping:
    def setup_method(self):
        self.task = make_task(
            Presentation.GROUP, QuestionType.GROUPING, group_size=4, num_units=1
        )
        self.unit = make_unit(self.task, ["i1", "i2", "i3", "i4"])

    def test_valid_partition(self):
        out = validate_answer(
            self.task, self.unit, {"groups": [["i1", "i4"], ["i2", "i3"]]}
        )
        assert out == {"groups": [["i1", "i4"], ["i2", "i3"]]}

    def test_overlap_rejected(self):
        with pytest.raises(AnswerValidationError):
            validate_answer(
                self.task, self.unit, {"groups": [["i1", "i2"], ["i2", "i3", "i4"]]}
            )

    def test_missing_item_rejected(self):
        with pytest.raises(AnswerValidationError):
            validate_answer(self.task, self.unit, {"groups": [["i1", "i2"], ["i3"]]})

    def test_empty_group_rejected(self):
        with pytest.raises(AnswerValidationError):
            validate_answer(
                self.task, self.unit, {"groups": [["i1", "i2", "i3", "i4"], []]}
            )
