from .conftest import create_project, upload_pngs


def setup_task(client, pid):
    return client.post(f"/api/projects/{pid}/tasks", json={
        "name": "cls", "presentation": "single", "question": "hard_label",
        "config": {"labels": ["cat", "dog"]},
    }).json()["task"]


def test_list_units_expands_items(client):
    pid = create_project(client)
    upload_pngs(client, pid, 3)
    task = setup_task(client, pid)
    units = client.get(f"/api/projects/{pid}/tasks/{task['id']}/units").json()
    assert len(units) == 3
    assert [u["position"] for u in units] == [0, 1, 2]
    assert units[0]["answer"] is None
    assert units[0]["items"][0]["modality"] == "image"


def test_save_annotation_updates_progress(client):
    pid = create_project(client)
    upload_pngs(client, pid, 2)
    task = setup_task(client, pid)
    units = client.get(f"/api/projects/{pid}/tasks/{task['id']}/units").json()

    res = client.put(
        f"/api/projects/{pid}/tasks/{task['id']}/units/{units[0]['id']}/annotation",
        json={"answer": {"label": "cat"}})
    assert res.status_code == 200
    assert res.json()["answer"] == {"label": "cat"}

    units = client.get(f"/api/projects/{pid}/tasks/{task['id']}/units").json()
    assert units[0]["answer"] == {"label": "cat"}
    tasks = client.get(f"/api/projects/{pid}/tasks").json()
    assert tasks[0]["answered_units"] == 1


def test_save_invalid_annotation_400(client):
    pid = create_project(client)
    upload_pngs(client, pid, 1)
    task = setup_task(client, pid)
    units = client.get(f"/api/projects/{pid}/tasks/{task['id']}/units").json()
    res = client.put(
        f"/api/projects/{pid}/tasks/{task['id']}/units/{units[0]['id']}/annotation",
        json={"answer": {"label": "bird"}})
    assert res.status_code == 400


def test_save_annotation_unknown_unit_404(client):
    pid = create_project(client)
    upload_pngs(client, pid, 1)
    task = setup_task(client, pid)
    res = client.put(
        f"/api/projects/{pid}/tasks/{task['id']}/units/nope/annotation",
        json={"answer": {"label": "cat"}})
    assert res.status_code == 404
