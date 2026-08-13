from .conftest import create_project, upload_pngs


def test_create_task_generates_units(client):
    pid = create_project(client)
    upload_pngs(client, pid, 4)
    res = client.post(f"/api/projects/{pid}/tasks", json={
        "name": "cls", "presentation": "single", "question": "hard_label",
        "config": {"labels": ["cat", "dog"]},
    })
    assert res.status_code == 201
    body = res.json()
    assert body["num_units"] == 4
    assert body["task"]["question"] == "hard_label"


def test_create_task_invalid_combination_400(client):
    pid = create_project(client)
    upload_pngs(client, pid, 4)
    res = client.post(f"/api/projects/{pid}/tasks", json={
        "name": "bad", "presentation": "single", "question": "preference",
        "config": {},
    })
    assert res.status_code == 400


def test_create_pair_task_without_num_units_400(client):
    pid = create_project(client)
    upload_pngs(client, pid, 4)
    res = client.post(f"/api/projects/{pid}/tasks", json={
        "name": "pref", "presentation": "pair", "question": "preference",
        "config": {},
    })
    assert res.status_code == 400


def test_list_tasks_with_progress(client):
    pid = create_project(client)
    upload_pngs(client, pid, 3)
    client.post(f"/api/projects/{pid}/tasks", json={
        "name": "cls", "presentation": "single", "question": "hard_label",
        "config": {"labels": ["a", "b"]},
    })
    tasks = client.get(f"/api/projects/{pid}/tasks").json()
    assert len(tasks) == 1
    assert tasks[0]["total_units"] == 3
    assert tasks[0]["answered_units"] == 0
