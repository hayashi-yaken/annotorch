import numpy as np
import torch
from torch.utils.data import DataLoader

from annotorch.datasets import load

from .conftest import create_project, upload_pngs

TO_TENSOR = lambda img: torch.from_numpy(np.array(img, dtype=np.float32) / 255.0)


def test_api_roundtrip_hard_label(client, tmp_path):
    pid = create_project(client, "rt")
    upload_pngs(client, pid, 4)
    task = client.post(f"/api/projects/{pid}/tasks", json={
        "name": "cls", "presentation": "single", "question": "hard_label",
        "config": {"labels": ["cat", "dog"]},
    }).json()["task"]

    units = client.get(f"/api/projects/{pid}/tasks/{task['id']}/units").json()
    for n, unit in enumerate(units):
        res = client.put(
            f"/api/projects/{pid}/tasks/{task['id']}/units/{unit['id']}/annotation",
            json={"answer": {"label": "cat" if n % 2 == 0 else "dog"}})
        assert res.status_code == 200

    out = tmp_path / "exported"
    res = client.post(f"/api/projects/{pid}/tasks/{task['id']}/export",
                      json={"output_dir": str(out)})
    assert res.status_code == 200
    assert res.json()["num_rows"] == 4

    ds = load(out, split="train", transform=TO_TENSOR)
    x, y = next(iter(DataLoader(ds, batch_size=4)))
    assert x.shape == (4, 8, 8, 3)
    assert sorted(y.tolist()) == [0, 0, 1, 1]


def test_api_roundtrip_preference_with_skip(client, tmp_path):
    pid = create_project(client, "rt-pref")
    upload_pngs(client, pid, 6)
    task = client.post(f"/api/projects/{pid}/tasks", json={
        "name": "pref", "presentation": "pair", "question": "preference",
        "config": {"num_units": 3, "seed": 0},
    }).json()["task"]

    units = client.get(f"/api/projects/{pid}/tasks/{task['id']}/units").json()
    answers = [{"winner": 1}, {"winner": None}, {"winner": -1}]
    for unit, answer in zip(units, answers):
        res = client.put(
            f"/api/projects/{pid}/tasks/{task['id']}/units/{unit['id']}/annotation",
            json={"answer": answer})
        assert res.status_code == 200

    out = tmp_path / "exported-pref"
    body = client.post(f"/api/projects/{pid}/tasks/{task['id']}/export",
                       json={"output_dir": str(out)}).json()
    assert body["num_rows"] == 2
    assert body["num_skipped"] == 1

    ds = load(out, split="train")
    assert [ds[n][1] for n in range(2)] == [1, -1]
