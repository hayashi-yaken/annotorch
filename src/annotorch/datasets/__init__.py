from __future__ import annotations

from pathlib import Path
from typing import Callable

from .base import AnnotorchDataset, read_manifest


def load(root: Path | str, split: str = "train",
         transform: Callable | None = None) -> AnnotorchDataset:
    """エクスポート済み annotorch データセットを読み込む。

    manifest の question と pairing に応じた Dataset サブクラスを返す。
    """
    task = read_manifest(root)["task"]
    question = task["question"]
    anchored = task.get("pairing", "random") == "anchor"
    if question == "hard_label":
        from .classification import HardLabelDataset as cls
    elif question == "soft_label":
        from .classification import SoftLabelDataset as cls
    elif question == "preference":
        if anchored:
            from .pair import AnchorPreferenceDataset as cls
        else:
            from .pair import PreferenceDataset as cls
    elif question == "similarity":
        if anchored:
            from .pair import AnchorSimilarityDataset as cls
        else:
            from .pair import SimilarityDataset as cls
    elif question == "ranking":
        from .group import RankingDataset as cls
    elif question == "grouping":
        from .group import GroupingDataset as cls
    else:
        raise ValueError(f"unsupported question type: {question}")
    return cls(root, split=split, transform=transform)
