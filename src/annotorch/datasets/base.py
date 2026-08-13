from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from PIL import Image
from torch.utils.data import Dataset


def read_manifest(root: Path | str) -> dict:
    manifest_path = Path(root) / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"not an annotorch dataset (no manifest.json): {root}")
    return json.loads(manifest_path.read_text())


class AnnotorchDataset(Dataset):
    """エクスポート済みデータセットの共通読み込み基盤。"""

    def __init__(self, root: Path | str, split: str = "train",
                 transform: Callable | None = None):
        self.root = Path(root)
        self.manifest = read_manifest(self.root)
        available = self.manifest.get("splits", {})
        if split not in available:
            raise ValueError(
                f"split {split!r} not in dataset (available: {sorted(available)})"
            )
        self.split = split
        self.transform = transform
        self._items: dict[str, dict] = {}
        for line in (self.root / "items.jsonl").read_text().splitlines():
            record = json.loads(line)
            self._items[record["id"]] = record
        self.rows: list[dict] = [
            row
            for line in (self.root / "annotations.jsonl").read_text().splitlines()
            if (row := json.loads(line))["split"] == split
        ]

    def _load_obj(self, item_id: str) -> Any:
        record = self._items[item_id]
        if "file" in record:
            with Image.open(self.root / record["file"]) as img:
                obj: Any = img.convert("RGB")
        else:
            obj = record["text"]
        if self.transform is not None:
            obj = self.transform(obj)
        return obj

    def __len__(self) -> int:
        return len(self.rows)
