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


def _create_hard_label_task(client, pid: str, name: str) -> str:
    return client.post(f"/api/projects/{pid}/tasks", json={
        "name": name, "presentation": "single", "question": "hard_label",
        "config": {"labels": ["a", "b"]},
    }).json()["task"]["id"]


def test_delete_task_removes_task_units_and_annotations(client):
    pid = create_project(client)
    upload_pngs(client, pid, 3)
    tid = _create_hard_label_task(client, pid, "cls")
    units = client.get(f"/api/projects/{pid}/tasks/{tid}/units").json()
    client.put(
        f"/api/projects/{pid}/tasks/{tid}/units/{units[0]['id']}/annotation",
        json={"answer": {"label": "a"}},
    )

    assert client.delete(f"/api/projects/{pid}/tasks/{tid}").status_code == 200

    assert client.get(f"/api/projects/{pid}/tasks").json() == []
    # units も消えているので、タスク越しの参照は 404 になる
    assert client.get(f"/api/projects/{pid}/tasks/{tid}/units").status_code == 404
    # 同じ設定でタスクを作り直すと、回答は引き継がれず未回答から始まる
    new_tid = _create_hard_label_task(client, pid, "cls2")
    new_units = client.get(f"/api/projects/{pid}/tasks/{new_tid}/units").json()
    assert [u["answer"] for u in new_units] == [None, None, None]


def test_delete_task_leaves_other_tasks_and_items(client):
    pid = create_project(client)
    upload_pngs(client, pid, 3)
    keep = _create_hard_label_task(client, pid, "keep")
    drop = _create_hard_label_task(client, pid, "drop")
    units = client.get(f"/api/projects/{pid}/tasks/{keep}/units").json()
    client.put(
        f"/api/projects/{pid}/tasks/{keep}/units/{units[0]['id']}/annotation",
        json={"answer": {"label": "a"}},
    )

    client.delete(f"/api/projects/{pid}/tasks/{drop}")

    tasks = client.get(f"/api/projects/{pid}/tasks").json()
    assert [t["id"] for t in tasks] == [keep]
    assert tasks[0]["answered_units"] == 1
    assert len(client.get(f"/api/projects/{pid}/items").json()) == 3


def test_delete_unknown_task_404(client):
    pid = create_project(client)
    assert client.delete(f"/api/projects/{pid}/tasks/nope").status_code == 404
