from __future__ import annotations

import random

from .models import Presentation, Task, Unit


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
