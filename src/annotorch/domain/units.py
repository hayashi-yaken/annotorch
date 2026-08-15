from __future__ import annotations

import random

from .models import Presentation, Task, Unit


def _anchor_units(task: Task, item_ids: list[str], rng: random.Random) -> list[Unit]:
    """アンカーを片側に固定したペアUnitを生成する。"""
    anchors = task.config.anchor_item_ids
    anchor_set, known = set(anchors), set(item_ids)
    unknown = [a for a in anchors if a not in known]
    if unknown:
        raise ValueError(f"unknown anchor item ids: {unknown}")

    n, k = task.config.num_units, len(anchors)
    if n < k:
        raise ValueError(
            f"anchor task requires num_units >= {k} anchors (got {n})"
        )
    candidates = [i for i in item_ids if i not in anchor_set]
    if n > len(candidates):
        raise ValueError(
            f"anchor task requires at least {n} non-anchor items for"
            f" num_units={n} (got {len(candidates)})"
        )

    partners = rng.sample(candidates, n)
    base, rem = divmod(n, k)
    assignment = [a for a in anchors for _ in range(base)]
    assignment += rng.sample(anchors, rem)
    rng.shuffle(assignment)

    units = []
    for pos, (anchor, partner) in enumerate(zip(assignment, partners)):
        ordered = [anchor, partner] if rng.random() < 0.5 else [partner, anchor]
        units.append(Unit(task_id=task.id, item_ids=ordered, position=pos))
    return units


def generate_units(task: Task, item_ids: list[str]) -> list[Unit]:
    """タスク定義に従って提示Unitを生成する。"""
    if task.presentation == Presentation.SINGLE:
        return [
            Unit(task_id=task.id, item_ids=[i], position=n)
            for n, i in enumerate(item_ids)
        ]

    rng = random.Random(task.config.seed)

    if task.presentation == Presentation.PAIR:
        if task.config.num_units is None:
            raise ValueError("pair task requires config.num_units")
        if task.config.pairing == "anchor":
            return _anchor_units(task, item_ids, rng)
        n = task.config.num_units
        if 2 * n > len(item_ids):
            raise ValueError(
                f"pair task requires at least {2 * n} items for num_units={n}"
                f" (got {len(item_ids)})"
            )
        picked = rng.sample(item_ids, 2 * n)
        return [
            Unit(task_id=task.id, item_ids=[picked[2 * p], picked[2 * p + 1]],
                 position=p)
            for p in range(n)
        ]

    if task.presentation == Presentation.GROUP:
        size = task.config.group_size
        if task.config.num_units is None or size is None:
            raise ValueError("group task requires config.num_units and config.group_size")
        if size < 2 or size > len(item_ids):
            raise ValueError(
                f"group_size must be in [2, {len(item_ids)}] (got {size})"
            )
        return [
            Unit(task_id=task.id, item_ids=rng.sample(item_ids, size), position=pos)
            for pos in range(task.config.num_units)
        ]

    raise ValueError(f"unsupported presentation: {task.presentation}")
