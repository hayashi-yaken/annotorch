import json
import sys

from PIL import Image

from annotorch.cli import main
from annotorch.domain.models import Presentation, QuestionType, TaskConfig
from annotorch.services.projects import ProjectService
from annotorch.services.tasks import TaskService
from annotorch.storage.workspace import Workspace


def setup_workspace(tmp_path):
    ws = Workspace(tmp_path / "root")
    projects, tasks = ProjectService(ws), TaskService(ws)
    project = projects.create("demo")
    src = tmp_path / "src"
    src.mkdir()
    for n in range(3):
        Image.new("RGB", (8, 8), (n * 50, 0, 0)).save(src / f"{n}.png")
    projects.import_images(project.id, src)
    task, _ = tasks.create_task(project.id, "cls", Presentation.SINGLE,
                                QuestionType.HARD_LABEL,
                                TaskConfig(labels=["cat", "dog"]))
    return project, task, tasks


def test_ls_lists_projects_and_tasks(tmp_path, capsys):
    project, task, _ = setup_workspace(tmp_path)
    code = main(["ls", "--root", str(tmp_path / "root")])
    out = capsys.readouterr().out
    assert code == 0
    assert project.id in out and "demo" in out
    assert task.id in out and "single/hard_label" in out


def test_export_end_to_end(tmp_path, capsys):
    project, task, tasks = setup_workspace(tmp_path)
    for unit, label in zip(tasks.list_units(project.id, task.id),
                           ["cat", "dog", "cat"]):
        tasks.save_answer(project.id, task.id, unit.id, {"label": label})

    out_dir = tmp_path / "exported"
    code = main([
        "export", "--root", str(tmp_path / "root"),
        "--project", project.id, "--task", task.id,
        "--out", str(out_dir), "--splits", "train=0.7,test=0.3", "--seed", "0",
    ])
    assert code == 0
    manifest = json.loads((out_dir / "manifest.json").read_text())
    assert manifest["task"]["question"] == "hard_label"
    assert str(out_dir) in capsys.readouterr().out


def test_export_error_is_reported(tmp_path, capsys):
    project, task, _ = setup_workspace(tmp_path)
    out_dir = tmp_path / "exists"
    out_dir.mkdir()
    code = main([
        "export", "--root", str(tmp_path / "root"),
        "--project", project.id, "--task", task.id, "--out", str(out_dir),
    ])
    assert code == 1
    assert "error" in capsys.readouterr().err.lower()


def test_serve_invokes_uvicorn(tmp_path, monkeypatch):
    calls = {}

    class FakeUvicorn:
        @staticmethod
        def run(app, host, port):
            calls["host"] = host
            calls["port"] = port

    monkeypatch.setitem(sys.modules, "uvicorn", FakeUvicorn)
    code = main(["serve", "--root", str(tmp_path), "--port", "9999", "--no-browser"])
    assert code == 0
    assert calls == {"host": "127.0.0.1", "port": 9999}
