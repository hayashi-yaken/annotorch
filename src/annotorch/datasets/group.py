from __future__ import annotations

import torch

from .base import AnnotorchDataset


class _GroupDataset(AnnotorchDataset):
    @staticmethod
    def collate_fn(batch):
        """可変長グループ用: バッチ次元はリストのまま返す。"""
        objs = [b[0] for b in batch]
        targets = [b[1] for b in batch]
        return objs, targets

    def _load_objs(self, row):
        return [self._load_obj(item_id) for item_id in row["item_ids"]]


class RankingDataset(_GroupDataset):
    def __getitem__(self, index: int):
        row = self.rows[index]
        order = row["answer"]["order"]
        ranks = torch.tensor(
            [order.index(item_id) for item_id in row["item_ids"]], dtype=torch.int64
        )
        return self._load_objs(row), ranks


class GroupingDataset(_GroupDataset):
    def __getitem__(self, index: int):
        row = self.rows[index]
        group_of = {
            item_id: g
            for g, group in enumerate(row["answer"]["groups"])
            for item_id in group
        }
        group_ids = torch.tensor(
            [group_of[item_id] for item_id in row["item_ids"]], dtype=torch.int64
        )
        return self._load_objs(row), group_ids
