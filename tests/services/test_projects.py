import json

import pytest
from PIL import Image

from annotorch.domain.models import Modality
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
