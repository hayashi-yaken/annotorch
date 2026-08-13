from __future__ import annotations

from .base import AnnotorchDataset


class _PairDataset(AnnotorchDataset):
    def _load_pair(self, row):
        id_a, id_b = row["item_ids"]
        return self._load_obj(id_a), self._load_obj(id_b)


class PreferenceDataset(_PairDataset):
    def __getitem__(self, index: int):
        row = self.rows[index]
        # winner: 1 = item_ids の1番目の勝ち, -1 = 2番目, 0 = tie（skip は除外済み）
        return self._load_pair(row), row["answer"]["winner"]


class SimilarityDataset(_PairDataset):
    def __getitem__(self, index: int):
        row = self.rows[index]
        answer = row["answer"]
        score = float(answer["same"]) if "same" in answer else float(answer["score"])
        return self._load_pair(row), score
