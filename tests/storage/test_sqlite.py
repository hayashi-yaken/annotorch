import pytest

from annotorch.domain.models import (
    Annotation,
    ItemsInUseError,
    Item,
    Modality,
    Presentation,
    Project,
    QuestionType,
    Task,
    TaskConfig,
    Unit,
)
from annotorch.storage.repository import ProjectStore
from annotorch.storage.sqlite import SqliteStore


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "project.db"


def make_task(project_id):
    return Task(
        project_id=project_id,
        name="classify",
        presentation=Presentation.SINGLE,
        question=QuestionType.HARD_LABEL,
        config=TaskConfig(labels=["cat", "dog"]),
    )


def test_sqlite_store_satisfies_protocol(db_path):
    store = SqliteStore(db_path)
    assert isinstance(store, ProjectStore)
    store.close()


def test_project_roundtrip_across_reopen(db_path):
    st = SqliteStore(db_path)
    project = Project(name="demo", description="d")
    st.add_project(project)
    st.close()

    st2 = SqliteStore(db_path)
    loaded = st2.get_project()
    assert loaded.id == project.id
    assert loaded.name == "demo"
    st2.close()


def test_get_project_empty_raises(db_path):
    st = SqliteStore(db_path)
    with pytest.raises(LookupError):
        st.get_project()


def test_items_roundtrip(db_path):
    st = SqliteStore(db_path)
    project = Project(name="demo")
    st.add_project(project)
    items = [
        Item(project_id=project.id, modality=Modality.IMAGE, path="a.png",
             metadata={"src": "x"}),
        Item(project_id=project.id, modality=Modality.TEXT, text="hello"),
    ]
    st.add_items(items)
    loaded = st.list_items(project.id)
    assert [i.id for i in loaded] == [i.id for i in items]
    assert loaded[0].metadata == {"src": "x"}
    assert loaded[1].text == "hello"


def test_task_and_units_roundtrip(db_path):
    st = SqliteStore(db_path)
    project = Project(name="demo")
    st.add_project(project)
    task = make_task(project.id)
    st.add_task(task)

    loaded_task = st.get_task(task.id)
    assert loaded_task.question == QuestionType.HARD_LABEL
    assert loaded_task.config.labels == ["cat", "dog"]

    units = [Unit(task_id=task.id, item_ids=[f"i{n}"], position=n) for n in range(3)]
    st.add_units(units)
    loaded_units = st.list_units(task.id)
    assert [u.position for u in loaded_units] == [0, 1, 2]
    assert loaded_units[1].item_ids == ["i1"]


def test_annotation_upsert(db_path):
    st = SqliteStore(db_path)
    project = Project(name="demo")
    st.add_project(project)
    task = make_task(project.id)
    st.add_task(task)
    unit = Unit(task_id=task.id, item_ids=["i0"], position=0)
    st.add_units([unit])
    annotator = st.get_default_annotator()

    st.save_annotation(
        Annotation(unit_id=unit.id, annotator_id=annotator.id, answer={"label": "cat"})
    )
    st.save_annotation(
        Annotation(unit_id=unit.id, annotator_id=annotator.id, answer={"label": "dog"})
    )
    anns = st.list_annotations_for_task(task.id)
    assert len(anns) == 1
    assert anns[0].answer == {"label": "dog"}


def test_default_annotator_is_stable(db_path):
    st = SqliteStore(db_path)
    a1 = st.get_default_annotator()
    a2 = st.get_default_annotator()
    assert a1.id == a2.id == "default"


def test_open_rejects_mismatched_schema_version(db_path):
    st = SqliteStore(db_path)
    st.conn.execute("UPDATE meta SET value = '999' WHERE key = 'schema_version'")
    st.conn.commit()
    st.close()

    with pytest.raises(RuntimeError, match="schema_version"):
        SqliteStore(db_path)


def test_delete_items_removes_only_the_given_rows(db_path):
    st = SqliteStore(db_path)
    project = Project(name="demo")
    st.add_project(project)
    items = [Item(project_id=project.id, modality=Modality.IMAGE, path=f"{n}.png")
             for n in range(3)]
    st.add_items(items)

    st.delete_items([items[0].id, items[2].id])

    assert [i.id for i in st.list_items(project.id)] == [items[1].id]


def test_delete_items_rejects_unknown_id_without_deleting_anything(db_path):
    st = SqliteStore(db_path)
    project = Project(name="demo")
    st.add_project(project)
    item = Item(project_id=project.id, modality=Modality.IMAGE, path="a.png")
    st.add_items([item])

    with pytest.raises(LookupError):
        st.delete_items([item.id, "nope"])

    assert [i.id for i in st.list_items(project.id)] == [item.id]


def test_delete_items_rejects_items_used_by_a_task(db_path):
    st = SqliteStore(db_path)
    project = Project(name="demo")
    st.add_project(project)
    items = [Item(project_id=project.id, modality=Modality.IMAGE, path=f"{n}.png")
             for n in range(2)]
    st.add_items(items)
    task = make_task(project.id)
    st.add_task(task)
    st.add_units([Unit(task_id=task.id, item_ids=[items[0].id], position=0)])

    with pytest.raises(ItemsInUseError) as excinfo:
        st.delete_items([items[0].id, items[1].id])

    assert excinfo.value.item_ids == [items[0].id]
    assert task.name in str(excinfo.value)
    assert len(st.list_items(project.id)) == 2


def test_delete_items_with_empty_list_is_a_noop(db_path):
    st = SqliteStore(db_path)
    project = Project(name="demo")
    st.add_project(project)
    item = Item(project_id=project.id, modality=Modality.IMAGE, path="a.png")
    st.add_items([item])

    st.delete_items([])

    assert [i.id for i in st.list_items(project.id)] == [item.id]
