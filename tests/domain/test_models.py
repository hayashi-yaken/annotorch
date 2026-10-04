import pytest
from pydantic import ValidationError

from annotorch.domain.models import (
    Item,
    Modality,
    Presentation,
    Project,
    QuestionType,
    Task,
    TaskConfig,
)


def test_project_gets_unique_id():
    a = Project(name="p1")
    b = Project(name="p2")
    assert a.id != b.id
    assert len(a.id) == 32  # uuid4().hex


def test_item_image_has_path():
    item = Item(project_id="p", modality=Modality.IMAGE, path="abc.png")
    assert item.text is None
    assert item.metadata == {}


def test_task_valid_combination():
    task = Task(
        project_id="p",
        name="classify",
        presentation=Presentation.SINGLE,
        question=QuestionType.HARD_LABEL,
        config=TaskConfig(labels=["cat", "dog"]),
    )
    assert task.config.labels == ["cat", "dog"]


def test_task_rejects_mismatched_presentation_question():
    with pytest.raises(ValidationError):
        Task(
            project_id="p",
            name="bad",
            presentation=Presentation.SINGLE,
            question=QuestionType.PREFERENCE,
            config=TaskConfig(),
        )


def test_label_task_requires_labels():
    with pytest.raises(ValidationError):
        Task(
            project_id="p",
            name="bad",
            presentation=Presentation.SINGLE,
            question=QuestionType.HARD_LABEL,
            config=TaskConfig(),
        )


def _anchor_task(presentation=Presentation.PAIR, question=QuestionType.PREFERENCE,
                 **config):
    return Task(project_id="p", name="a", presentation=presentation,
                question=question, config=TaskConfig(num_units=2, **config))


def test_anchor_task_valid():
    task = _anchor_task(pairing="anchor", anchor_item_ids=["a"])
    assert task.config.anchor_item_ids == ["a"]
    assert task.config.pairing == "anchor"


def test_pairing_defaults_to_random():
    assert TaskConfig().pairing == "random"
    assert TaskConfig().anchor_item_ids is None


def test_anchor_pairing_rejects_non_pair_presentation():
    with pytest.raises(ValidationError):
        _anchor_task(presentation=Presentation.GROUP, question=QuestionType.RANKING,
                     group_size=2, pairing="anchor", anchor_item_ids=["a"])


def test_anchor_pairing_requires_anchor_ids():
    with pytest.raises(ValidationError):
        _anchor_task(pairing="anchor")


def test_random_pairing_rejects_anchor_ids():
    with pytest.raises(ValidationError):
        _anchor_task(anchor_item_ids=["a"])


def test_anchor_ids_must_be_unique():
    with pytest.raises(ValidationError, match="found: .* 'a'"):
        _anchor_task(pairing="anchor", anchor_item_ids=["a", "a"])


def test_confidence_task_needs_no_labels():
    task = Task(project_id="p", name="quality", presentation=Presentation.SINGLE,
                question=QuestionType.CONFIDENCE)
    assert task.question == QuestionType.CONFIDENCE


def test_confidence_task_accepts_two_end_labels():
    task = Task(project_id="p", name="bird", presentation=Presentation.SINGLE,
                question=QuestionType.CONFIDENCE,
                config=TaskConfig(labels=["swan", "duck"]))
    assert task.config.labels == ["swan", "duck"]


@pytest.mark.parametrize("labels", [["swan"], ["swan", "duck", "goose"]])
def test_confidence_labels_must_be_two_ends(labels):
    with pytest.raises(ValidationError, match="exactly 2"):
        Task(project_id="p", name="bird", presentation=Presentation.SINGLE,
             question=QuestionType.CONFIDENCE, config=TaskConfig(labels=labels))


def test_confidence_task_rejects_pair_presentation():
    with pytest.raises(ValidationError):
        Task(project_id="p", name="quality", presentation=Presentation.PAIR,
             question=QuestionType.CONFIDENCE)
