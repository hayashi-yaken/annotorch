import json

import pytest
from PIL import Image

from annotorch.domain.models import (
    ItemsInUseError,
    Modality,
    Presentation,
    QuestionType,
    Task,
    TaskConfig,
    Unit,
)
from annotorch.services.projects import ProjectService
from annotorch.storage.workspace import Workspace


@pytest.fixture
def svc(tmp_path):
    return ProjectService(Workspace(tmp_path / "root"))


def make_png(path, color=(255, 0, 0)):
    Image.new("RGB", (8, 8), color).save(path)


def test_create_list_delete(svc):
    p = svc.create("demo", "desc")
    assert [x.id for x in svc.list()] == [p.id]
    svc.delete(p.id)
    assert svc.list() == []


def test_import_images_copies_and_reports(svc, tmp_path):
    project = svc.create("demo")
    src = tmp_path / "src"
    (src / "sub").mkdir(parents=True)
    make_png(src / "a.png")
    make_png(src / "sub" / "b.png")
    (src / "notes.md").write_text("not an image")
    (src / "broken.png").write_bytes(b"not really a png")

    report = svc.import_images(project.id, src)

    assert report.imported == 2
    reasons = {s.source: s.reason for s in report.skipped}
    assert any("notes.md" in k for k in reasons)
    assert any("broken.png" in k for k in reasons)

    items = svc.list_items(project.id)
    assert len(items) == 2
    for item in items:
        assert item.modality == Modality.IMAGE
        assert svc.item_file_path(project.id, item.id).exists()
        assert item.metadata["source"].endswith(".png")


def test_item_file_path_unknown_raises(svc):
    project = svc.create("demo")
    with pytest.raises(LookupError):
        svc.item_file_path(project.id, "nope")


def test_import_images_empty_dir_does_not_crash(svc, tmp_path):
    project = svc.create("demo")
    src = tmp_path / "empty"
    src.mkdir()
    assert svc.import_images(project.id, src).imported == 0


def test_import_texts_jsonl(svc, tmp_path):
    project = svc.create("demo")
    p = tmp_path / "texts.jsonl"
    lines = [
        json.dumps({"text": "hello", "topic": "greeting"}),
        "{broken json",
        json.dumps({"no_text_key": 1}),
        json.dumps({"text": "world"}),
    ]
    p.write_text("\n".join(lines))
    report = svc.import_texts_jsonl(project.id, p)

    assert report.imported == 2
    assert len(report.skipped) == 2
    items = svc.list_items(project.id)
    assert items[0].text == "hello"
    assert items[0].metadata == {"topic": "greeting"}


def test_import_texts_csv(svc, tmp_path):
    project = svc.create("demo")
    p = tmp_path / "texts.csv"
    p.write_text("text,topic\nhello,greeting\nworld,place\n")
    report = svc.import_texts_csv(project.id, p)
    assert report.imported == 2
    items = svc.list_items(project.id)
    assert items[1].text == "world"
    assert items[1].metadata == {"topic": "place"}


def test_import_texts_csv_missing_column(svc, tmp_path):
    project = svc.create("demo")
    p = tmp_path / "bad.csv"
    p.write_text("body\nhello\n")
    report = svc.import_texts_csv(project.id, p)
    assert report.imported == 0
    assert len(report.skipped) == 1
    assert "text" in report.skipped[0].reason


def test_import_texts_csv_short_row_skipped(svc, tmp_path):
    """text列がヘッダ末尾にあると、列数が足りない行は DictReader の restval で
    text=None になる (欠損とみなして安全にスキップする)。"""
    project = svc.create("demo")
    p = tmp_path / "short.csv"
    p.write_text("topic,text\ngreeting,hello\nonlytopic\nplace,world\n")
    report = svc.import_texts_csv(project.id, p)
    assert report.imported == 2
    assert len(report.skipped) == 1
    assert "text" in report.skipped[0].reason
    items = svc.list_items(project.id)
    assert [i.text for i in items] == ["hello", "world"]


def test_delete_items_removes_the_files_from_disk(svc, tmp_path):
    project = svc.create("demo")
    src = tmp_path / "src"
    src.mkdir()
    make_png(src / "a.png")
    make_png(src / "b.png", (0, 255, 0))
    svc.import_images(project.id, src)
    items = svc.list_items(project.id)
    items_dir = svc.ws.items_dir(project.id)

    svc.delete_items(project.id, [items[0].id])

    assert [i.id for i in svc.list_items(project.id)] == [items[1].id]
    assert not (items_dir / items[0].path).exists()
    assert (items_dir / items[1].path).exists()


def test_delete_items_keeps_files_when_an_item_is_in_use(svc, tmp_path):
    project = svc.create("demo")
    src = tmp_path / "src"
    src.mkdir()
    make_png(src / "a.png")
    svc.import_images(project.id, src)
    item = svc.list_items(project.id)[0]
    with svc.ws.open(project.id) as store:
        task = Task(project_id=project.id, name="classify",
                    presentation=Presentation.SINGLE,
                    question=QuestionType.HARD_LABEL,
                    config=TaskConfig(labels=["cat"]))
        store.add_task(task)
        store.add_units([Unit(task_id=task.id, item_ids=[item.id], position=0)])

    with pytest.raises(ItemsInUseError):
        svc.delete_items(project.id, [item.id])

    assert (svc.ws.items_dir(project.id) / item.path).exists()
    assert len(svc.list_items(project.id)) == 1
