import json

import pytest
from PIL import Image

from annotorch.domain.models import Presentation, QuestionType, TaskConfig
from annotorch.services.exports import ExportService
from annotorch.services.projects import ProjectService
from annotorch.services.tasks import TaskService
from annotorch.storage.workspace import Workspace


@pytest.fixture
def env(tmp_path):
    """3枚の画像 + hard_label タスク + 2件回答済み(1件未回答)の環境。"""
    ws = Workspace(tmp_path / "root")
    projects, tasks, exports = ProjectService(ws), TaskService(ws), ExportService(ws)
    project = projects.create("demo")
    src = tmp_path / "src"
    src.mkdir()
    for n in range(3):
        Image.new("RGB", (8, 8), (n * 40, 0, 0)).save(src / f"{n}.png")
    projects.import_images(project.id, src)
    task, _ = tasks.create_task(project.id, "cls", Presentation.SINGLE,
                                QuestionType.HARD_LABEL,
                                TaskConfig(labels=["cat", "dog"]))
    units = tasks.list_units(project.id, task.id)
    for unit, label in zip(units[:2], ["cat", "dog"]):
        tasks.save_answer(project.id, task.id, unit.id, {"label": label})
    return project, task, exports, tmp_path


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_export_layout_and_content(env):
    project, task, exports, tmp_path = env
    out = tmp_path / "dataset"
    result = exports.export(project.id, task.id, out)

    assert result.num_rows == 2
    assert result.num_unanswered_units == 1

    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["format_version"] == 1
    assert manifest["task"]["question"] == "hard_label"
    assert manifest["classes"] == ["cat", "dog"]
    assert manifest["modality"] == "image"
    assert manifest["splits"] == {"train": 2}

    rows = read_jsonl(out / "annotations.jsonl")
    assert len(rows) == 2
    assert rows[0]["answer"] == {"label": "cat"}
    assert rows[0]["split"] == "train"

    index = {r["id"]: r for r in read_jsonl(out / "items.jsonl")}
    for row in rows:
        for item_id in row["item_ids"]:
            assert (out / index[item_id]["file"]).exists()


def test_export_splits_are_unit_level_and_seeded(env):
    project, task, exports, tmp_path = env
    r1 = exports.export(project.id, task.id, tmp_path / "d1",
                        splits={"train": 0.5, "test": 0.5}, seed=0)
    assert sum(r1.split_counts.values()) == 2

    exports.export(project.id, task.id, tmp_path / "d2",
                   splits={"train": 0.5, "test": 0.5}, seed=0)
    rows1 = read_jsonl(tmp_path / "d1" / "annotations.jsonl")
    rows2 = read_jsonl(tmp_path / "d2" / "annotations.jsonl")
    assert [(r["unit_id"], r["split"]) for r in rows1] == \
           [(r["unit_id"], r["split"]) for r in rows2]


def test_export_refuses_existing_output(env):
    project, task, exports, tmp_path = env
    out = tmp_path / "dataset"
    out.mkdir()
    with pytest.raises(FileExistsError):
        exports.export(project.id, task.id, out)


def test_export_cleans_tmp_on_failure(env):
    project, task, exports, tmp_path = env
    # 画像実体を消して途中失敗させる
    items_dir = tmp_path / "root" / "projects" / project.id / "items"
    for f in items_dir.iterdir():
        f.unlink()
    out = tmp_path / "dataset"
    with pytest.raises(FileNotFoundError):
        exports.export(project.id, task.id, out)
    assert not out.exists()
    assert not list(tmp_path.glob(".*.tmp"))


def test_invalid_splits_rejected(env):
    project, task, exports, tmp_path = env
    with pytest.raises(ValueError):
        exports.export(project.id, task.id, tmp_path / "x",
                       splits={"train": 0.5, "test": 0.2})


def test_negative_split_fraction_rejected(env):
    """合計が1になっても、個々の分割が(0, 1]の範囲外なら拒否する。"""
    project, task, exports, tmp_path = env
    with pytest.raises(ValueError):
        exports.export(project.id, task.id, tmp_path / "x",
                       splits={"train": 1.5, "test": -0.5})
