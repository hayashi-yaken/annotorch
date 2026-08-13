import pytest

from annotorch.domain.models import Presentation, QuestionType, Task, TaskConfig
from annotorch.domain.units import generate_units

ITEMS = [f"i{n}" for n in range(6)]


def make_task(presentation, question, **config):
    return Task(project_id="p", name="t", presentation=presentation,
                question=question, config=TaskConfig(**config))


def test_single_one_unit_per_item():
    task = make_task(Presentation.SINGLE, QuestionType.HARD_LABEL, labels=["a"])
    units = generate_units(task, ITEMS)
    assert [u.item_ids for u in units] == [[i] for i in ITEMS]
    assert [u.position for u in units] == list(range(6))


def test_pair_units_are_distinct_pairs():
    task = make_task(Presentation.PAIR, QuestionType.PREFERENCE, num_units=10, seed=42)
    units = generate_units(task, ITEMS)
    assert len(units) == 10
    seen = set()
    for u in units:
        assert len(u.item_ids) == 2
        pair = frozenset(u.item_ids)
        assert pair not in seen
        seen.add(pair)


def test_pair_deterministic_by_seed():
    task = make_task(Presentation.PAIR, QuestionType.PREFERENCE, num_units=5, seed=1)
    a = [u.item_ids for u in generate_units(task, ITEMS)]
    b = [u.item_ids for u in generate_units(task, ITEMS)]
    assert a == b


def test_pair_capped_at_all_pairs():
    task = make_task(Presentation.PAIR, QuestionType.PREFERENCE, num_units=999, seed=0)
    units = generate_units(task, ITEMS)
    assert len(units) == 15  # C(6,2)


def test_pair_requires_num_units():
    task = make_task(Presentation.PAIR, QuestionType.PREFERENCE)
    with pytest.raises(ValueError):
        generate_units(task, ITEMS)


def test_group_units():
    task = make_task(Presentation.GROUP, QuestionType.RANKING,
                     num_units=4, group_size=3, seed=7)
    units = generate_units(task, ITEMS)
    assert len(units) == 4
    for u in units:
        assert len(u.item_ids) == 3
        assert len(set(u.item_ids)) == 3


def test_group_size_too_large():
    task = make_task(Presentation.GROUP, QuestionType.RANKING,
                     num_units=1, group_size=7)
    with pytest.raises(ValueError):
        generate_units(task, ITEMS)
