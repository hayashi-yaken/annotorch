"""ラウンドトリップテスト:
services 経由で プロジェクト作成 → インポート → タスク作成 → 回答 → エクスポート
→ datasets.load → DataLoader 1周 を全質問タイプで検証する。
"""
import json

import numpy as np
import pytest
import torch
from PIL import Image
from torch.utils.data import DataLoader

from annotorch.domain.models import Presentation, QuestionType, TaskConfig
from annotorch.services.exports import ExportService
from annotorch.services.projects import ProjectService
from annotorch.services.tasks import TaskService
from annotorch.storage.workspace import Workspace
from annotorch.datasets import load

TO_TENSOR = lambda img: torch.from_numpy(np.array(img, dtype=np.float32) / 255.0)
NUM_ITEMS = 6


@pytest.fixture
def env(tmp_path):
    ws = Workspace(tmp_path / "root")
    services = (ProjectService(ws), TaskService(ws), ExportService(ws))
    project = services[0].create("rt")
    src = tmp_path / "src"
    src.mkdir()
    for n in range(NUM_ITEMS):
        Image.new("RGB", (8, 8), (n * 40 % 256, 10, 10)).save(src / f"{n}.png")
    report = services[0].import_images(project.id, src)
    assert report.imported == NUM_ITEMS
    return project, services, tmp_path


def run_task(project, services, out_dir, name, presentation, question, config,
             answer_fn, transform=None):
    """タスク作成→全Unit回答→エクスポート→load して ds を返す。"""
    _, tasks, exports = services
    task, _ = tasks.create_task(project.id, name, presentation, question, config)
    for unit in tasks.list_units(project.id, task.id):
        tasks.save_answer(project.id, task.id, unit.id, answer_fn(unit))
    result = exports.export(project.id, task.id, out_dir)
    assert result.num_unanswered_units == 0
    return load(out_dir, split="train", transform=transform)


def test_roundtrip_hard_label_image(env):
    project, services, tmp_path = env
    ds = run_task(project, services, tmp_path / "ds", "hard",
                  Presentation.SINGLE, QuestionType.HARD_LABEL,
                  TaskConfig(labels=["red", "dark"]),
                  lambda u: {"label": "red"}, transform=TO_TENSOR)
    assert len(ds) == NUM_ITEMS
    x, y = next(iter(DataLoader(ds, batch_size=4)))
    assert x.shape == (4, 8, 8, 3)
    assert y.tolist() == [0, 0, 0, 0]


def test_roundtrip_soft_label_image(env):
    project, services, tmp_path = env
    ds = run_task(project, services, tmp_path / "ds", "soft",
                  Presentation.SINGLE, QuestionType.SOFT_LABEL,
                  TaskConfig(labels=["red", "dark"]),
                  lambda u: {"dist": {"red": 0.6, "dark": 0.4}}, transform=TO_TENSOR)
    x, y = next(iter(DataLoader(ds, batch_size=2)))
    assert y.shape == (2, 2)
    assert torch.allclose(y.sum(dim=1), torch.ones(2))


def test_roundtrip_preference_image(env):
    project, services, tmp_path = env
    ds = run_task(project, services, tmp_path / "ds", "pref",
                  Presentation.PAIR, QuestionType.PREFERENCE,
                  TaskConfig(num_units=5, seed=3),
                  lambda u: {"winner": 1}, transform=TO_TENSOR)
    assert len(ds) == 5
    assert "preference_winner" in ds.manifest["conventions"]
    (xa, xb), w = next(iter(DataLoader(ds, batch_size=5)))
    assert xa.shape == (5, 8, 8, 3)
    assert w.tolist() == [1] * 5  # 1 = item_ids の1番目の勝ち


def test_roundtrip_preference_skip_excluded(env):
    project, services, tmp_path = env
    _, tasks, exports = services
    task, _ = tasks.create_task(project.id, "prefskip", Presentation.PAIR,
                                QuestionType.PREFERENCE,
                                TaskConfig(num_units=4, seed=3))
    units = tasks.list_units(project.id, task.id)
    answers = [{"winner": 1}, {"winner": None}, {"winner": -1}, {"winner": None}]
    for unit, ans in zip(units, answers):
        tasks.save_answer(project.id, task.id, unit.id, ans)
    result = exports.export(project.id, task.id, tmp_path / "ds-skip")
    assert result.num_rows == 2
    assert result.num_skipped == 2
    ds = load(tmp_path / "ds-skip")
    assert len(ds) == 2


def test_roundtrip_similarity_binary_image(env):
    project, services, tmp_path = env
    ds = run_task(project, services, tmp_path / "ds", "sim",
                  Presentation.PAIR, QuestionType.SIMILARITY,
                  TaskConfig(similarity_mode="binary", num_units=4, seed=1),
                  lambda u: {"same": True})
    (_, _), score = ds[0]
    assert score == 1.0


def test_roundtrip_ranking_image(env):
    project, services, tmp_path = env
    ds = run_task(project, services, tmp_path / "ds", "rank",
                  Presentation.GROUP, QuestionType.RANKING,
                  TaskConfig(group_size=3, num_units=3, seed=5),
                  lambda u: {"order": [i.id for i in reversed(u.items)]},
                  transform=TO_TENSOR)
    loader = DataLoader(ds, batch_size=3, collate_fn=ds.collate_fn)
    obj_lists, rank_list = next(iter(loader))
    assert len(obj_lists) == 3
    # 逆順回答なので提示順 j のアイテムの順位は (2 - j)
    assert rank_list[0].tolist() == [2, 1, 0]


def test_roundtrip_grouping_image(env):
    project, services, tmp_path = env

    def group_answer(unit):
        ids = [i.id for i in unit.items]
        return {"groups": [ids[:2], ids[2:]]}

    ds = run_task(project, services, tmp_path / "ds", "grp",
                  Presentation.GROUP, QuestionType.GROUPING,
                  TaskConfig(group_size=4, num_units=2, seed=5),
                  group_answer)
    objs, group_ids = ds[0]
    assert len(objs) == 4
    assert group_ids.tolist() == [0, 0, 1, 1]


def test_roundtrip_hard_label_text(tmp_path):
    ws = Workspace(tmp_path / "root")
    projects, tasks, exports = ProjectService(ws), TaskService(ws), ExportService(ws)
    project = projects.create("rt-text")
    jsonl = tmp_path / "texts.jsonl"
    jsonl.write_text("\n".join(
        json.dumps({"text": f"document {n}"}) for n in range(4)
    ))
    assert projects.import_texts_jsonl(project.id, jsonl).imported == 4

    task, _ = tasks.create_task(project.id, "topic", Presentation.SINGLE,
                                QuestionType.HARD_LABEL,
                                TaskConfig(labels=["news", "spam"]))
    for unit in tasks.list_units(project.id, task.id):
        tasks.save_answer(project.id, task.id, unit.id, {"label": "news"})
    exports.export(project.id, task.id, tmp_path / "ds-text")

    ds = load(tmp_path / "ds-text")
    obj, label = ds[0]
    assert obj == "document 0"
    assert label == 0


def test_roundtrip_non_ascii_text_and_label(tmp_path):
    """日本語テキストとラベルが export/load を通じて破損しない (utf-8 明示のリグレッション)。"""
    ws = Workspace(tmp_path / "root")
    projects, tasks, exports = ProjectService(ws), TaskService(ws), ExportService(ws)
    project = projects.create("rt-ja")
    jsonl = tmp_path / "texts.jsonl"
    jsonl.write_text(
        json.dumps({"text": "これは猫です"}, ensure_ascii=False), encoding="utf-8"
    )
    assert projects.import_texts_jsonl(project.id, jsonl).imported == 1

    task, _ = tasks.create_task(project.id, "topic", Presentation.SINGLE,
                                QuestionType.HARD_LABEL,
                                TaskConfig(labels=["猫", "犬"]))
    for unit in tasks.list_units(project.id, task.id):
        tasks.save_answer(project.id, task.id, unit.id, {"label": "猫"})
    exports.export(project.id, task.id, tmp_path / "ds-ja")

    manifest = json.loads((tmp_path / "ds-ja" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["classes"] == ["猫", "犬"]

    ds = load(tmp_path / "ds-ja")
    obj, label = ds[0]
    assert obj == "これは猫です"
    assert label == 0


def test_roundtrip_with_splits(env):
    project, services, tmp_path = env
    _, tasks, exports = services
    task, _ = tasks.create_task(project.id, "split", Presentation.SINGLE,
                                QuestionType.HARD_LABEL,
                                TaskConfig(labels=["red", "dark"]))
    for unit in tasks.list_units(project.id, task.id):
        tasks.save_answer(project.id, task.id, unit.id, {"label": "red"})
    exports.export(project.id, task.id, tmp_path / "ds-split",
                   splits={"train": 0.5, "test": 0.5}, seed=0)
    train = load(tmp_path / "ds-split", split="train")
    test = load(tmp_path / "ds-split", split="test")
    assert len(train) + len(test) == NUM_ITEMS
    assert len(train) > 0 and len(test) > 0
