import logging

import pytest

from .conftest import create_project, upload_pngs

LOGGER = "annotorch.server"


def records(caplog, level):
    return [r for r in caplog.records if r.name == LOGGER and r.levelno == level]


@pytest.fixture(autouse=True)
def _capture(caplog):
    caplog.set_level(logging.WARNING, logger=LOGGER)


def test_not_found_is_404_and_logged(client, caplog):
    res = client.delete("/api/projects/nope")
    assert res.status_code == 404
    assert "no project nope" in res.json()["detail"]
    [r] = records(caplog, logging.WARNING)
    assert r.getMessage().startswith(
        "DELETE /api/projects/nope -> 404 NotFoundError: no project nope")


def test_invalid_input_is_400_and_logged(client, caplog):
    pid = create_project(client)
    res = client.patch(f"/api/projects/{pid}", json={"name": " "})
    assert res.status_code == 400
    assert res.json() == {"detail": "project name must not be empty"}
    [r] = records(caplog, logging.WARNING)
    assert r.getMessage() == (
        f"PATCH /api/projects/{pid} -> 400 InvalidInputError: project name must not be empty")


def test_answer_validation_is_400_with_its_own_type(client, caplog):
    pid = create_project(client)
    upload_pngs(client, pid, 1)
    tid = client.post(f"/api/projects/{pid}/tasks", json={
        "name": "q", "presentation": "single", "question": "confidence", "config": {},
    }).json()["task"]["id"]
    [unit] = client.get(f"/api/projects/{pid}/tasks/{tid}/units").json()
    res = client.put(f"/api/projects/{pid}/tasks/{tid}/units/{unit['id']}/annotation",
                     json={"answer": {"score": 1.5}})
    assert res.status_code == 400
    [r] = records(caplog, logging.WARNING)
    assert "-> 400 AnswerValidationError: score must be between 0 and 1" in r.getMessage()


def test_conflict_is_409_and_logged(client, caplog):
    pid = create_project(client)
    upload_pngs(client, pid, 2)
    client.post(f"/api/projects/{pid}/tasks", json={
        "name": "cls", "presentation": "single", "question": "hard_label",
        "config": {"labels": ["a", "b"]},
    })
    ids = [i["id"] for i in client.get(f"/api/projects/{pid}/items").json()]
    res = client.request("DELETE", f"/api/projects/{pid}/items", json={"item_ids": ids})
    assert res.status_code == 409
    [r] = records(caplog, logging.WARNING)
    assert "-> 409 ItemsInUseError: 2 item(s) are still used by task(s): cls" in r.getMessage()


def test_unexpected_exception_is_500_logged_once_with_traceback(client, caplog, monkeypatch):
    pid = create_project(client)

    def broken(project_id):
        return {}["missing"]

    monkeypatch.setattr(client.app.state.projects, "list_items", broken)
    res = client.get(f"/api/projects/{pid}/items")
    assert res.status_code == 500
    assert res.json() == {"detail": "internal server error (see server log)"}
    [r] = records(caplog, logging.ERROR)
    assert r.getMessage() == f"GET /api/projects/{pid}/items -> 500 KeyError: 'missing'"
    assert r.exc_info is not None
    assert records(caplog, logging.WARNING) == []


def test_missing_item_file_is_500_and_names_the_path(client, caplog, tmp_path):
    pid = create_project(client)
    upload_pngs(client, pid, 1)
    [item] = client.get(f"/api/projects/{pid}/items").json()
    (tmp_path / "root" / "projects" / pid / "items" / item["path"]).unlink()
    res = client.get(f"/api/projects/{pid}/items/{item['id']}/file")
    assert res.status_code == 500
    [r] = records(caplog, logging.ERROR)
    assert "-> 500 ItemFileMissingError" in r.getMessage()
    assert item["path"] in r.getMessage()


def test_request_validation_is_422_and_logged(client, caplog):
    res = client.post("/api/projects", json={})
    assert res.status_code == 422
    [r] = records(caplog, logging.WARNING)
    assert r.getMessage().startswith("POST /api/projects -> 422 RequestValidationError:")
    assert "name" in r.getMessage()
