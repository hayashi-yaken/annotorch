from __future__ import annotations

import torch

from .base import AnnotorchDataset


class _LabeledDataset(AnnotorchDataset):
    def __init__(self, root, split="train", transform=None):
        super().__init__(root, split=split, transform=transform)
        self.classes: list[str] = list(self.manifest["classes"])
        self.class_to_idx: dict[str, int] = {c: n for n, c in enumerate(self.classes)}


class HardLabelDataset(_LabeledDataset):
    def __getitem__(self, index: int):
        row = self.rows[index]
        obj = self._load_obj(row["item_ids"][0])
        return obj, self.class_to_idx[row["answer"]["label"]]


class SoftLabelDataset(_LabeledDataset):
    def __getitem__(self, index: int):
        row = self.rows[index]
        obj = self._load_obj(row["item_ids"][0])
        dist = row["answer"]["dist"]
        target = torch.tensor(
            [dist.get(c, 0.0) for c in self.classes], dtype=torch.float32
        )
        return obj, target
