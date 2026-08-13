from __future__ import annotations

from pathlib import Path
from typing import Callable

from .base import AnnotorchDataset, read_manifest


def load(root: Path | str, split: str = "train",
         transform: Callable | None = None) -> AnnotorchDataset:
    """エクスポート済み annotorch データセットを読み込む。

    manifest の question に応じた Dataset サブクラスを返す。
    """
    question = read_manifest(root)["task"]["question"]
    if question == "hard_label":
        from .classification import HardLabelDataset as cls
    elif question == "soft_label":
        from .classification import SoftLabelDataset as cls
    elif question == "preference":
        from .pair import PreferenceDataset as cls
    elif question == "similarity":
        from .pair import SimilarityDataset as cls
    elif question == "ranking":
        from .group import RankingDataset as cls
    elif question == "grouping":
        from .group import GroupingDataset as cls
    else:
        raise ValueError(f"unsupported question type: {question}")
    return cls(root, split=split, transform=transform)
