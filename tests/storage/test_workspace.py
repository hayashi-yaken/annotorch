import pytest

from annotorch.storage.sqlite import SqliteStore
from annotorch.storage.workspace import Workspace


def test_create_project_makes_layout(tmp_path):
    ws = Workspace(tmp_path)
    project = ws.create_project("demo", "desc")
    assert (tmp_path / "projects" / project.id / "project.db").exists()
    assert ws.items_dir(project.id).is_dir()


def test_list_projects(tmp_path):
    ws = Workspace(tmp_path)
    a = ws.create_project("a")
    b = ws.create_project("b")
    assert {p.name for p in ws.list_projects()} == {"a", "b"}
    assert {p.id for p in ws.list_projects()} == {a.id, b.id}


def test_open_yields_store_and_closes(tmp_path):
    ws = Workspace(tmp_path)
    project = ws.create_project("demo")
    with ws.open(project.id) as store:
        assert store.get_project().name == "demo"
    # close 済みの接続は使えない
    import sqlite3
    with pytest.raises(sqlite3.ProgrammingError):
        store.get_project()


def test_open_unknown_project_raises(tmp_path):
    ws = Workspace(tmp_path)
    with pytest.raises(LookupError):
        with ws.open("nope"):
            pass


def test_delete_project(tmp_path):
    ws = Workspace(tmp_path)
    p = ws.create_project("demo")
    ws.delete_project(p.id)
    assert ws.list_projects() == []
    with pytest.raises(LookupError):
        ws.delete_project(p.id)


def test_list_projects_skips_projectless_db(tmp_path):
    """半端に作られた project.db (プロジェクト行なし) が listing 全体を壊さない。"""
    ws = Workspace(tmp_path)
    healthy = ws.create_project("healthy")

    broken_dir = tmp_path / "projects" / "broken-id"
    broken_dir.mkdir(parents=True)
    store = SqliteStore(broken_dir / "project.db")
    store.close()

    projects = ws.list_projects()
    assert [p.id for p in projects] == [healthy.id]


def test_create_project_cleans_up_dir_on_failure(tmp_path, monkeypatch):
    ws = Workspace(tmp_path)

    def boom(self, p):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(SqliteStore, "add_project", boom)
    with pytest.raises(RuntimeError):
        ws.create_project("demo")

    assert list((tmp_path / "projects").glob("*")) == []
