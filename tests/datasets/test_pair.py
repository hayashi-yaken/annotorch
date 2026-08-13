import numpy as np
import torch
from torch.utils.data import DataLoader

from annotorch.datasets import load

from .test_classification import write_dataset

TO_TENSOR = lambda img: torch.from_numpy(np.array(img, dtype=np.float32) / 255.0)


def pair_rows(answers):
    return [
        {"unit_id": f"u{n}", "item_ids": ["a", "b"], "answer": ans,
         "annotator_id": "default", "split": "train"}
        for n, ans in enumerate(answers)
    ]


def patch_manifest(root, question):
    import json
    manifest = json.loads((root / "manifest.json").read_text())
    manifest["task"]["presentation"] = "pair"
    manifest["task"]["question"] = question
    (root / "manifest.json").write_text(json.dumps(manifest))


def test_preference_sign_convention(tmp_path):
    rows = pair_rows([{"winner": 1}, {"winner": -1}, {"winner": 0}])
    write_dataset(tmp_path, "preference", None, rows, image_ids=["a", "b"])
    patch_manifest(tmp_path, "preference")
    ds = load(tmp_path, split="train")
    winners = [ds[n][1] for n in range(3)]
    assert winners == [1, -1, 0]
    (obj_a, obj_b), _ = ds[0]
    assert obj_a is not None and obj_b is not None


def test_preference_dataloader_batches(tmp_path):
    rows = pair_rows([{"winner": 1}, {"winner": -1}])
    write_dataset(tmp_path, "preference", None, rows, image_ids=["a", "b"])
    patch_manifest(tmp_path, "preference")
    ds = load(tmp_path, split="train", transform=TO_TENSOR)
    (batch_a, batch_b), batch_w = next(iter(DataLoader(ds, batch_size=2)))
    assert batch_a.shape == (2, 8, 8, 3)
    assert batch_w.tolist() == [1, -1]


def test_similarity_continuous(tmp_path):
    rows = pair_rows([{"score": 0.8}])
    write_dataset(tmp_path, "similarity", None, rows, image_ids=["a", "b"])
    patch_manifest(tmp_path, "similarity")
    ds = load(tmp_path, split="train")
    (_, _), score = ds[0]
    assert score == 0.8


def test_similarity_binary_maps_to_float(tmp_path):
    rows = pair_rows([{"same": True}, {"same": False}])
    write_dataset(tmp_path, "similarity", None, rows, image_ids=["a", "b"])
    patch_manifest(tmp_path, "similarity")
    ds = load(tmp_path, split="train")
    assert ds[0][1] == 1.0
    assert ds[1][1] == 0.0
