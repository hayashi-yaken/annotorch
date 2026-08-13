import torch
from torch.utils.data import DataLoader

from annotorch.datasets import load

from .test_classification import write_dataset


def patch_manifest(root, question):
    import json
    manifest = json.loads((root / "manifest.json").read_text())
    manifest["task"]["presentation"] = "group"
    manifest["task"]["question"] = question
    (root / "manifest.json").write_text(json.dumps(manifest))


def test_ranking_dataset(tmp_path):
    rows = [{
        "unit_id": "u0",
        "item_ids": ["a", "b", "c"],
        "answer": {"order": ["c", "a", "b"]},  # c が最良
        "annotator_id": "default", "split": "train",
    }]
    write_dataset(tmp_path, "ranking", None, rows, image_ids=["a", "b", "c"])
    patch_manifest(tmp_path, "ranking")
    ds = load(tmp_path, split="train")
    objs, ranks = ds[0]
    assert len(objs) == 3
    # a は order[1] → rank 1, b は order[2] → rank 2, c は order[0] → rank 0
    assert ranks.tolist() == [1, 2, 0]
    assert ranks.dtype == torch.int64


def test_grouping_dataset(tmp_path):
    rows = [{
        "unit_id": "u0",
        "item_ids": ["a", "b", "c", "d"],
        "answer": {"groups": [["a", "d"], ["b", "c"]]},
        "annotator_id": "default", "split": "train",
    }]
    write_dataset(tmp_path, "grouping", None, rows, image_ids=["a", "b", "c", "d"])
    patch_manifest(tmp_path, "grouping")
    ds = load(tmp_path, split="train")
    objs, group_ids = ds[0]
    assert len(objs) == 4
    assert group_ids.tolist() == [0, 1, 1, 0]


def test_group_collate_fn_with_variable_sizes(tmp_path):
    rows = [
        {"unit_id": "u0", "item_ids": ["a", "b", "c"],
         "answer": {"order": ["a", "b", "c"]},
         "annotator_id": "default", "split": "train"},
        {"unit_id": "u1", "item_ids": ["a", "b"],
         "answer": {"order": ["b", "a"]},
         "annotator_id": "default", "split": "train"},
    ]
    write_dataset(tmp_path, "ranking", None, rows, image_ids=["a", "b", "c"])
    patch_manifest(tmp_path, "ranking")
    ds = load(tmp_path, split="train")
    loader = DataLoader(ds, batch_size=2, collate_fn=ds.collate_fn)
    obj_lists, rank_list = next(iter(loader))
    assert len(obj_lists) == 2
    assert len(obj_lists[0]) == 3 and len(obj_lists[1]) == 2
    assert rank_list[1].tolist() == [1, 0]
