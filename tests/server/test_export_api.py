import pytest

from .conftest import create_project, upload_pngs


def make_task(client, pid):
    return client.post(f"/api/projects/{pid}/tasks", json={
        "name": "cls", "presentation": "single", "question": "hard_label",
        "config": {"labels": ["cat", "dog"]},
    }).json()["task"]


def annotate_all(client, pid, task_id, labels=("cat", "dog")):
    units = client.get(f"/api/projects/{pid}/tasks/{task_id}/units").json()
    for n, unit in enumerate(units):
        client.put(
            f"/api/projects/{pid}/tasks/{task_id}/units/{unit['id']}/annotation",
            json={"answer": {"label": labels[n % len(labels)]}})


@pytest.fixture
def annotated(client):
    pid = create_project(client)
    upload_pngs(client, pid, 4)
    task = make_task(client, pid)
    annotate_all(client, pid, task["id"])
    return f"/api/projects/{pid}/tasks/{task['id']}/export"


def test_export_writes_under_export_root(client, tmp_path, annotated):
    res = client.post(annotated, json={"name": "ds"})
    assert res.status_code == 200
    assert res.json()["num_rows"] == 4
    out = tmp_path / "export" / "ds"
    assert res.json()["output_dir"] == str(out.resolve())
    assert (out / "manifest.json").exists()


def test_export_existing_name_409(client, tmp_path, annotated):
    (tmp_path / "export" / "ds").mkdir(parents=True)
    res = client.post(annotated, json={"name": "ds"})
    assert res.status_code == 409


@pytest.mark.parametrize("name", ["../escape", "/tmp/x", "a/b", ".hidden", " "])
def test_export_rejects_names_that_are_paths_400(client, tmp_path, annotated, name):
    res = client.post(annotated, json={"name": name})
    assert res.status_code == 400
    assert not (tmp_path / "escape").exists()


def test_export_invalid_splits_400(client, annotated):
    res = client.post(annotated, json={"name": "x",
                                       "splits": {"train": 0.5, "test": 0.2}})
    assert res.status_code == 400
