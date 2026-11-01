import io
import json
import zipfile
from pathlib import Path

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


def test_export_zip_returns_dataset_in_named_folder(client, tmp_path, annotated):
    res = client.post(f"{annotated}/zip", json={"name": "ds",
                                                "splits": {"train": 0.5, "test": 0.5}})
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/zip"
    assert 'filename="ds.zip"' in res.headers["content-disposition"]
    with zipfile.ZipFile(io.BytesIO(res.content)) as zf:
        names = zf.namelist()
        manifest = json.loads(zf.read("ds/manifest.json"))
    assert "ds/annotations.jsonl" in names
    assert sum(1 for n in names if n.startswith("ds/items/") and n.endswith(".png")) == 4
    assert manifest["splits"] == {"train": 2, "test": 2}
    assert not (tmp_path / "export" / "ds").exists()


def test_export_zip_supports_non_ascii_name(client, annotated):
    res = client.post(f"{annotated}/zip", json={"name": "白鳥"})
    assert res.status_code == 200
    assert "filename*=utf-8''%E7%99%BD%E9%B3%A5.zip" in res.headers["content-disposition"]


def test_export_zip_rejects_bad_name_400(client, annotated):
    res = client.post(f"{annotated}/zip", json={"name": "../x"})
    assert res.status_code == 400


def test_export_zip_invalid_splits_400(client, annotated):
    res = client.post(f"{annotated}/zip", json={"name": "x", "splits": {"train": 2}})
    assert res.status_code == 400


def test_export_zip_leaves_no_temporary_files(client, annotated, monkeypatch, tmp_path):
    from annotorch.server.routers import export as export_router

    made = []
    real_mkdtemp = export_router.tempfile.mkdtemp

    def mkdtemp(**kw):
        made.append(real_mkdtemp(dir=tmp_path, **kw))
        return made[-1]

    monkeypatch.setattr(export_router.tempfile, "mkdtemp", mkdtemp)
    assert client.post(f"{annotated}/zip", json={"name": "ds"}).status_code == 200
    assert client.post(f"{annotated}/zip", json={"name": "../x"}).status_code == 400
    assert len(made) == 1 and not Path(made[0]).exists()


def test_zip_stream_removes_workdir_before_streaming(tmp_path):
    from annotorch.server.routers.export import open_archive_once

    workdir = tmp_path / "work"
    workdir.mkdir()
    archive = workdir / "ds.zip"
    archive.write_bytes(b"x" * 10)

    size, chunks = open_archive_once(archive, workdir, chunk_size=4)
    assert size == 10
    assert not workdir.exists()
    assert b"".join(chunks) == b"x" * 10


def test_zip_stream_closes_file_when_abandoned(tmp_path):
    from annotorch.server.routers.export import open_archive_once

    workdir = tmp_path / "work"
    workdir.mkdir()
    archive = workdir / "ds.zip"
    archive.write_bytes(b"x" * 10)

    _, chunks = open_archive_once(archive, workdir, chunk_size=4)
    next(chunks)
    chunks.close()
    assert not workdir.exists()


def test_export_zip_quotes_filename_with_double_quote(client, annotated):
    res = client.post(f"{annotated}/zip", json={"name": 'a"b'})
    assert res.status_code == 200
    assert res.headers["content-disposition"] == "attachment; filename*=utf-8''a%22b.zip"
