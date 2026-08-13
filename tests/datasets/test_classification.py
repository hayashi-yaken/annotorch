import json

import numpy as np
import pytest
import torch
from PIL import Image
from torch.utils.data import DataLoader

from annotorch.datasets import load


def write_dataset(root, question, classes, rows, image_ids=(), text_items=()):
    """エクスポート形式のデータセットを直接書き出すテストヘルパ。"""
    (root / "items").mkdir(parents=True)
    with open(root / "items.jsonl", "w") as f:
        for n, item_id in enumerate(image_ids):
            fname = f"items/{item_id}.png"
            Image.new("RGB", (8, 8), (n * 30 % 256, 0, 0)).save(root / fname)
            f.write(json.dumps({"id": item_id, "modality": "image",
                                "file": fname, "metadata": {}}) + "\n")
        for item_id, text in text_items:
            f.write(json.dumps({"id": item_id, "modality": "text",
                                "text": text, "metadata": {}}) + "\n")
    split_counts = {}
    with open(root / "annotations.jsonl", "w") as f:
        for row in rows:
            split_counts[row["split"]] = split_counts.get(row["split"], 0) + 1
            f.write(json.dumps(row) + "\n")
    manifest = {
        "format_version": 1,
        "generator": "test",
        "task": {"name": "t", "presentation": "single", "question": question},
        "classes": classes,
        "modality": "image" if image_ids else "text",
        "aggregation": "raw",
        "conventions": {},
        "seed": 0,
        "splits": split_counts,
    }
    (root / "manifest.json").write_text(json.dumps(manifest))


TO_TENSOR = lambda img: torch.from_numpy(np.array(img, dtype=np.float32) / 255.0)


def hard_rows(image_ids, labels):
    return [
        {"unit_id": f"u{n}", "item_ids": [i], "answer": {"label": lb},
         "annotator_id": "default", "split": "train"}
        for n, (i, lb) in enumerate(zip(image_ids, labels))
    ]


def test_hard_label_dataset(tmp_path):
    ids = ["a", "b", "c"]
    write_dataset(tmp_path, "hard_label", ["cat", "dog"],
                  hard_rows(ids, ["cat", "dog", "cat"]), image_ids=ids)
    ds = load(tmp_path, split="train")
    assert len(ds) == 3
    assert ds.classes == ["cat", "dog"]
    obj, label = ds[1]
    assert isinstance(obj, Image.Image)
    assert label == 1


def test_hard_label_with_transform_and_dataloader(tmp_path):
    ids = ["a", "b", "c"]
    write_dataset(tmp_path, "hard_label", ["cat", "dog"],
                  hard_rows(ids, ["cat", "dog", "cat"]), image_ids=ids)
    ds = load(tmp_path, split="train", transform=TO_TENSOR)
    batch_x, batch_y = next(iter(DataLoader(ds, batch_size=3)))
    assert batch_x.shape == (3, 8, 8, 3)
    assert batch_y.tolist() == [0, 1, 0]


def test_soft_label_dataset(tmp_path):
    ids = ["a", "b"]
    rows = [
        {"unit_id": "u0", "item_ids": ["a"], "answer": {"dist": {"cat": 0.7, "dog": 0.3}},
         "annotator_id": "default", "split": "train"},
        {"unit_id": "u1", "item_ids": ["b"], "answer": {"dist": {"dog": 1.0}},
         "annotator_id": "default", "split": "train"},
    ]
    write_dataset(tmp_path, "soft_label", ["cat", "dog"], rows, image_ids=ids)
    ds = load(tmp_path, split="train")
    _, dist = ds[0]
    assert isinstance(dist, torch.Tensor)
    assert dist.dtype == torch.float32
    assert torch.allclose(dist, torch.tensor([0.7, 0.3]))
    _, dist1 = ds[1]
    assert torch.allclose(dist1, torch.tensor([0.0, 1.0]))


def test_text_modality(tmp_path):
    rows = hard_rows(["t1"], ["cat"])
    write_dataset(tmp_path, "hard_label", ["cat", "dog"], rows,
                  text_items=[("t1", "hello world")])
    ds = load(tmp_path, split="train")
    obj, label = ds[0]
    assert obj == "hello world"
    assert label == 0


def test_unknown_split_raises(tmp_path):
    ids = ["a"]
    write_dataset(tmp_path, "hard_label", ["cat", "dog"],
                  hard_rows(ids, ["cat"]), image_ids=ids)
    with pytest.raises(ValueError):
        load(tmp_path, split="test")
