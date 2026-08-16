from collections import Counter

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


def test_pair_items_are_not_reused():
    task = make_task(Presentation.PAIR, QuestionType.PREFERENCE, num_units=3, seed=42)
    units = generate_units(task, ITEMS)
    assert len(units) == 3
    used = [i for u in units for i in u.item_ids]
    assert len(used) == 6
    assert len(set(used)) == 6


def test_pair_uses_every_item_when_budget_matches():
    task = make_task(Presentation.PAIR, QuestionType.PREFERENCE, num_units=3, seed=1)
    units = generate_units(task, ITEMS)
    assert {i for u in units for i in u.item_ids} == set(ITEMS)


def test_pair_leaves_remainder_when_budget_is_smaller():
    task = make_task(Presentation.PAIR, QuestionType.PREFERENCE, num_units=2, seed=1)
    units = generate_units(task, ITEMS)
    assert len({i for u in units for i in u.item_ids}) == 4


def test_pair_seed_changes_result():
    a = [u.item_ids for u in generate_units(
        make_task(Presentation.PAIR, QuestionType.PREFERENCE, num_units=3, seed=1), ITEMS)]
    b = [u.item_ids for u in generate_units(
        make_task(Presentation.PAIR, QuestionType.PREFERENCE, num_units=3, seed=2), ITEMS)]
    assert a != b


def test_pair_errors_when_items_insufficient():
    task = make_task(Presentation.PAIR, QuestionType.PREFERENCE, num_units=4, seed=0)
    with pytest.raises(ValueError, match="at least 8 items"):
        generate_units(task, ITEMS)


def test_pair_deterministic_by_seed():
    task = make_task(Presentation.PAIR, QuestionType.PREFERENCE, num_units=3, seed=1)
    a = [u.item_ids for u in generate_units(task, ITEMS)]
    b = [u.item_ids for u in generate_units(task, ITEMS)]
    assert a == b


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


ANCHORS = ["i0", "i1"]


def make_anchor_task(num_units, seed=0, anchors=ANCHORS):
    return make_task(Presentation.PAIR, QuestionType.PREFERENCE,
                     num_units=num_units, seed=seed,
                     pairing="anchor", anchor_item_ids=anchors)


def test_anchor_every_unit_has_exactly_one_anchor():
    units = generate_units(make_anchor_task(4, seed=3), ITEMS)
    assert len(units) == 4
    for u in units:
        assert len(u.item_ids) == 2
        assert len([i for i in u.item_ids if i in ANCHORS]) == 1


def test_anchor_partners_are_not_reused():
    units = generate_units(make_anchor_task(4, seed=3), ITEMS)
    partners = [i for u in units for i in u.item_ids if i not in ANCHORS]
    assert sorted(partners) == ["i2", "i3", "i4", "i5"]


def test_anchor_counts_are_balanced():
    for seed in range(10):
        units = generate_units(make_anchor_task(3, seed=seed), ITEMS)
        counts = Counter(i for u in units for i in u.item_ids if i in ANCHORS)
        assert sorted(counts.values()) == [1, 2]


def test_anchor_deterministic_by_seed():
    a = [u.item_ids for u in generate_units(make_anchor_task(4, seed=5), ITEMS)]
    b = [u.item_ids for u in generate_units(make_anchor_task(4, seed=5), ITEMS)]
    assert a == b


def test_anchor_side_is_shuffled():
    orders = {
        u.item_ids[0] in ANCHORS
        for seed in range(5)
        for u in generate_units(make_anchor_task(4, seed=seed), ITEMS)
    }
    assert orders == {True, False}


def test_anchor_errors_when_partners_insufficient():
    with pytest.raises(ValueError, match="non-anchor items"):
        generate_units(make_anchor_task(5), ITEMS)


def test_anchor_errors_when_budget_below_anchor_count():
    with pytest.raises(ValueError, match="num_units"):
        generate_units(make_anchor_task(1, anchors=["i0", "i1", "i2"]), ITEMS)


def test_anchor_errors_on_unknown_anchor_id():
    with pytest.raises(ValueError, match="unknown anchor"):
        generate_units(make_anchor_task(2, anchors=["i0", "zzz"]), ITEMS)
