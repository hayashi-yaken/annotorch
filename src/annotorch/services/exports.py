from __future__ import annotations

import json
import random
import shutil
from pathlib import Path

from pydantic import BaseModel, Field

from .. import __version__
from ..domain.models import QuestionType
from ..storage.repository import ProjectStore
from ..storage.workspace import Workspace

FORMAT_VERSION = 1


class ExportResult(BaseModel):
    output_dir: Path
    num_rows: int
    num_unanswered_units: int
    num_skipped: int
    split_counts: dict[str, int] = Field(default_factory=dict)


class ExportService:
    """アノテーション済みタスクの自己完結データセットへの書き出し。"""

    def __init__(self, workspace: Workspace):
        self.ws = workspace

    def export(self, project_id: str, task_id: str, output_dir: Path,
               splits: dict[str, float] | None = None, seed: int = 0) -> ExportResult:
        if splits is not None:
            if not splits:
                raise ValueError("splits must not be empty")
            for name, fraction in splits.items():
                if not (0 < fraction <= 1):
                    raise ValueError(
                        f"split fraction for {name!r} must be in (0, 1] (got {fraction})"
                    )
            total = sum(splits.values())
            if abs(total - 1.0) > 1e-3:
                raise ValueError(f"split fractions must sum to 1 (got {total})")
        with self.ws.open(project_id) as store:
            return _export(store, task_id, self.ws.items_dir(project_id),
                           Path(output_dir), splits, seed)


def _assign_splits(
    unit_ids: list[str], splits: dict[str, float] | None, seed: int
) -> dict[str, str]:
    if not splits:
        return {u: "train" for u in unit_ids}
    shuffled = list(unit_ids)
    random.Random(seed).shuffle(shuffled)
    assignment: dict[str, str] = {}
    names = list(splits)
    n = len(shuffled)
    start = 0
    cumulative = 0.0
    for k, name in enumerate(names):
        cumulative += splits[name]
        end = n if k == len(names) - 1 else round(cumulative * n)
        for u in shuffled[start:end]:
            assignment[u] = name
        start = end
    return assignment


def _export(store: ProjectStore, task_id: str, items_dir: Path,
            output_dir: Path, splits: dict[str, float] | None,
            seed: int) -> ExportResult:
    task = store.get_task(task_id)
    units = {u.id: u for u in store.list_units(task_id)}
    annotations = store.list_annotations_for_task(task_id)

    num_skipped = 0
    rows_source = []
    answered_unit_ids: list[str] = []
    for a in annotations:
        if task.question == QuestionType.PREFERENCE and a.answer.get("winner") is None:
            num_skipped += 1
            continue
        rows_source.append(a)
        if a.unit_id not in answered_unit_ids:
            answered_unit_ids.append(a.unit_id)
    num_unanswered = len(units) - len({a.unit_id for a in annotations})

    split_of = _assign_splits(answered_unit_ids, splits, seed)

    referenced_item_ids: list[str] = []
    for a in rows_source:
        for item_id in units[a.unit_id].item_ids:
            if item_id not in referenced_item_ids:
                referenced_item_ids.append(item_id)
    all_items = {i.id: i for i in store.list_items(task.project_id)}

    if output_dir.exists():
        raise FileExistsError(f"output already exists: {output_dir}")
    tmp = output_dir.parent / f".{output_dir.name}.tmp"
    if tmp.exists():
        shutil.rmtree(tmp)

    try:
        (tmp / "items").mkdir(parents=True)

        modalities = set()
        with open(tmp / "items.jsonl", "w", encoding="utf-8") as f:
            for item_id in referenced_item_ids:
                item = all_items[item_id]
                modalities.add(item.modality.value)
                if item.path is not None:
                    src = items_dir / item.path
                    if not src.exists():
                        raise FileNotFoundError(f"item file missing: {src}")
                    shutil.copy2(src, tmp / "items" / item.path)
                    record = {"id": item.id, "modality": item.modality.value,
                              "file": f"items/{item.path}", "metadata": item.metadata}
                else:
                    record = {"id": item.id, "modality": item.modality.value,
                              "text": item.text, "metadata": item.metadata}
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

        anchor_ids = set(task.config.anchor_item_ids or [])
        used_anchors: list[str] = []

        split_counts: dict[str, int] = {}
        with open(tmp / "annotations.jsonl", "w", encoding="utf-8") as f:
            for a in rows_source:
                split = split_of[a.unit_id]
                split_counts[split] = split_counts.get(split, 0) + 1
                row = {
                    "unit_id": a.unit_id,
                    "item_ids": units[a.unit_id].item_ids,
                    "answer": a.answer,
                    "annotator_id": a.annotator_id,
                    "split": split,
                }
                if anchor_ids:
                    anchor = next(i for i in units[a.unit_id].item_ids
                                  if i in anchor_ids)
                    row["anchor_item_id"] = anchor
                    if anchor not in used_anchors:
                        used_anchors.append(anchor)
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

        modality = modalities.pop() if len(modalities) == 1 else (
            "mixed" if modalities else "empty"
        )
        conventions: dict[str, str] = {}
        if task.question == QuestionType.PREFERENCE:
            conventions["preference_winner"] = (
                "1 = first item in item_ids wins, -1 = second, 0 = tie"
            )
        if anchor_ids:
            conventions["anchor_item_id"] = (
                "the fixed reference item of the pair;"
                " the other entry in item_ids varies"
            )

        manifest = {
            "format_version": FORMAT_VERSION,
            "generator": f"annotorch {__version__}",
            "task": {"name": task.name, "presentation": task.presentation.value,
                     "question": task.question.value,
                     "pairing": task.config.pairing},
            "classes": task.config.labels,
            "modality": modality,
            "aggregation": "raw",
            "conventions": conventions,
            "seed": seed,
            "splits": split_counts,
        }
        if anchor_ids:
            manifest["anchors"] = used_anchors
        (tmp / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        tmp.rename(output_dir)
    except BaseException:
        if tmp.exists():
            shutil.rmtree(tmp)
        raise

    return ExportResult(
        output_dir=output_dir,
        num_rows=len(rows_source),
        num_unanswered_units=num_unanswered,
        num_skipped=num_skipped,
        split_counts=split_counts,
    )
