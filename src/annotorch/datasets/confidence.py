from __future__ import annotations

from .base import AnnotorchDataset


class ConfidenceDataset(AnnotorchDataset):
    def __getitem__(self, index: int):
        row = self.rows[index]
        obj = self._load_obj(row["item_ids"][0])
        return obj, float(row["answer"]["score"])
