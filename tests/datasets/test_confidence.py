from annotorch.datasets import load

from .test_classification import write_dataset


def test_confidence_returns_the_score_as_a_float(tmp_path):
    write_dataset(
        tmp_path, "confidence", None,
        [
            {"unit_id": "u1", "item_ids": ["i1"], "answer": {"score": 0.8},
             "annotator_id": "a", "split": "train"},
            {"unit_id": "u2", "item_ids": ["i2"], "answer": {"score": 0.0},
             "annotator_id": "a", "split": "train"},
        ],
        image_ids=["i1", "i2"],
    )

    ds = load(tmp_path, split="train")

    assert type(ds).__name__ == "ConfidenceDataset"
    assert len(ds) == 2
    obj, score = ds[0]
    assert obj.size == (8, 8)
    assert score == 0.8
    assert isinstance(score, float)
    assert ds[1][1] == 0.0
