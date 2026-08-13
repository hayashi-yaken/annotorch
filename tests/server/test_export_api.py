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


def test_export(client, tmp_path):
    pid = create_project(client)
    upload_pngs(client, pid, 4)
    task = make_task(client, pid)
    annotate_all(client, pid, task["id"])

    out = tmp_path / "ds"
    res = client.post(f"/api/projects/{pid}/tasks/{task['id']}/export",
                      json={"output_dir": str(out)})
    assert res.status_code == 200
    assert res.json()["num_rows"] == 4
    assert (out / "manifest.json").exists()


def test_export_existing_dir_409(client, tmp_path):
    pid = create_project(client)
    upload_pngs(client, pid, 1)
    task = make_task(client, pid)
    annotate_all(client, pid, task["id"])
    out = tmp_path / "ds"
    out.mkdir()
    res = client.post(f"/api/projects/{pid}/tasks/{task['id']}/export",
                      json={"output_dir": str(out)})
    assert res.status_code == 409


def test_export_invalid_splits_400(client, tmp_path):
    pid = create_project(client)
    upload_pngs(client, pid, 1)
    task = make_task(client, pid)
    annotate_all(client, pid, task["id"])
    res = client.post(f"/api/projects/{pid}/tasks/{task['id']}/export",
                      json={"output_dir": str(tmp_path / "x"),
                            "splits": {"train": 0.5, "test": 0.2}})
    assert res.status_code == 400
