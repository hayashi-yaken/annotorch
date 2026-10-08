import pytest
from PIL import Image

from annotorch.domain.models import Presentation, QuestionType, TaskConfig
from annotorch.errors import AnswerValidationError, InvalidInputError, NotFoundError
from annotorch.services.projects import ProjectService
from annotorch.services.tasks import TaskService
from annotorch.storage.workspace import Workspace


@pytest.fixture
def env(tmp_path):
    ws = Workspace(tmp_path / "root")
    projects = ProjectService(ws)
    tasks = TaskService(ws)
    project = projects.create("demo")
    src = tmp_path / "src"
    src.mkdir()
    for n in range(4):
        Image.new("RGB", (8, 8), (n * 50, 0, 0)).save(src / f"{n}.png")
    projects.import_images(project.id, src)
    return project, tasks


def test_create_task_generates_units(env):
    project, tasks = env
    task, num_units = tasks.create_task(
        project.id, "cls", Presentation.SINGLE, QuestionType.HARD_LABEL,
        TaskConfig(labels=["cat", "dog"]))
    assert num_units == 4
    assert task.question == QuestionType.HARD_LABEL


def test_rename_task_persists(env):
    project, tasks = env
    task, _ = tasks.create_task(
        project.id, "cls", Presentation.SINGLE, QuestionType.HARD_LABEL,
        TaskConfig(labels=["cat", "dog"]))
    renamed = tasks.rename_task(project.id, task.id, "  birds  ")
    assert renamed.name == "birds"
    [listed] = tasks.list_tasks_with_progress(project.id)
    assert (listed.id, listed.name, listed.config) == (task.id, "birds", task.config)


def test_rename_task_rejects_blank_name(env):
    project, tasks = env
    task, _ = tasks.create_task(
        project.id, "cls", Presentation.SINGLE, QuestionType.HARD_LABEL,
        TaskConfig(labels=["cat", "dog"]))
    with pytest.raises(InvalidInputError):
        tasks.rename_task(project.id, task.id, " ")
    assert tasks.list_tasks_with_progress(project.id)[0].name == "cls"


def test_rename_unknown_task_raises(env):
    project, tasks = env
    with pytest.raises(NotFoundError):
        tasks.rename_task(project.id, "nope", "x")


def test_create_task_invalid_combination_raises(env):
    project, tasks = env
    with pytest.raises(InvalidInputError):
        tasks.create_task(project.id, "bad", Presentation.SINGLE,
                          QuestionType.PREFERENCE, TaskConfig())


def test_create_pair_task_without_num_units_raises(env):
    project, tasks = env
    with pytest.raises(InvalidInputError):
        tasks.create_task(project.id, "pref", Presentation.PAIR,
                          QuestionType.PREFERENCE, TaskConfig())


def test_progress_and_units_flow(env):
    project, tasks = env
    task, _ = tasks.create_task(
        project.id, "cls", Presentation.SINGLE, QuestionType.HARD_LABEL,
        TaskConfig(labels=["cat", "dog"]))

    listed = tasks.list_tasks_with_progress(project.id)
    assert listed[0].total_units == 4
    assert listed[0].answered_units == 0

    units = tasks.list_units(project.id, task.id)
    assert [u.position for u in units] == [0, 1, 2, 3]
    assert units[0].answer is None
    assert units[0].items[0].modality.value == "image"

    saved = tasks.save_answer(project.id, task.id, units[0].id, {"label": "cat"})
    assert saved == {"label": "cat"}

    units = tasks.list_units(project.id, task.id)
    assert units[0].answer == {"label": "cat"}
    assert tasks.list_tasks_with_progress(project.id)[0].answered_units == 1


def test_save_answer_invalid_raises(env):
    project, tasks = env
    task, _ = tasks.create_task(
        project.id, "cls", Presentation.SINGLE, QuestionType.HARD_LABEL,
        TaskConfig(labels=["cat", "dog"]))
    units = tasks.list_units(project.id, task.id)
    with pytest.raises(AnswerValidationError):
        tasks.save_answer(project.id, task.id, units[0].id, {"label": "bird"})


def test_save_answer_unknown_unit_raises(env):
    project, tasks = env
    task, _ = tasks.create_task(
        project.id, "cls", Presentation.SINGLE, QuestionType.HARD_LABEL,
        TaskConfig(labels=["cat", "dog"]))
    with pytest.raises(NotFoundError):
        tasks.save_answer(project.id, task.id, "nope", {"label": "cat"})
