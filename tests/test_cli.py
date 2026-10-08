import json

import pytest
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


def _run_serve(monkeypatch, tmp_path, *extra):
    import uvicorn

    captured = {}
    monkeypatch.setattr(uvicorn, "run", lambda app, **kw: captured.update(kw))
    code = main(["serve", "--root", str(tmp_path / "root"), "--no-browser", *extra])
    assert code == 0
    return captured


def test_serve_invokes_uvicorn(tmp_path, monkeypatch):
    kw = _run_serve(monkeypatch, tmp_path, "--port", "9999")
    assert (kw["host"], kw["port"]) == ("127.0.0.1", 9999)


def test_serve_log_level_defaults_to_info(tmp_path, monkeypatch):
    monkeypatch.delenv("ANNOTORCH_LOG_LEVEL", raising=False)
    kw = _run_serve(monkeypatch, tmp_path)
    assert kw["log_level"] == "info"
    assert kw["log_config"]["loggers"]["annotorch"]["level"] == "INFO"


def test_serve_log_level_from_env(tmp_path, monkeypatch):
    monkeypatch.setenv("ANNOTORCH_LOG_LEVEL", "debug")
    assert _run_serve(monkeypatch, tmp_path)["log_level"] == "debug"


def test_serve_log_level_flag_beats_env(tmp_path, monkeypatch):
    monkeypatch.setenv("ANNOTORCH_LOG_LEVEL", "debug")
    assert _run_serve(monkeypatch, tmp_path, "--log-level", "warning")["log_level"] == "warning"


def test_serve_log_level_env_is_case_insensitive(tmp_path, monkeypatch):
    monkeypatch.setenv("ANNOTORCH_LOG_LEVEL", "DEBUG")
    assert _run_serve(monkeypatch, tmp_path)["log_level"] == "debug"


def test_serve_rejects_unknown_log_level_env(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("ANNOTORCH_LOG_LEVEL", "warn")
    with pytest.raises(SystemExit) as excinfo:
        main(["serve", "--root", str(tmp_path / "root"), "--no-browser"])
    assert excinfo.value.code == 2
    assert "ANNOTORCH_LOG_LEVEL" in capsys.readouterr().err
