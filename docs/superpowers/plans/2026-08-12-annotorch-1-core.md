# annotorch 計画1: Python コア層 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** レイヤード構造の Python コア層（domain / storage / services / datasets）を完成させる。インポート→アノテーション→エクスポート→`DataLoader` 読み込みがコードだけで一巡できる状態（ラウンドトリップテストで検証）。UI は計画3で実装し、本計画はその土台となる。

**Architecture:** 依存方向が一方通行のレイヤードモノリス。`domain`（純粋モデル・検証・Unit生成）← `storage`（ProjectStore Protocol + SQLite実装 + Workspace）← `services`（ProjectService / TaskService / ExportService = ユースケースの唯一の入口）。`datasets` はどのレイヤーにも依存せず、エクスポート成果物のファイル形式だけを読む。HTTP（計画2）と CLI は services を呼ぶ薄いアダプタになる。

**Tech Stack:** Python 3.11+（開発は3.13）、uv、pydantic v2、sqlite3（標準ライブラリ）、Pillow、numpy、torch、pytest。

**参照スペック:** `docs/superpowers/specs/2026-08-12-annotorch-design.md`

## Global Constraints

- 作業ディレクトリ: `/Users/hayashinaofumi/workspace/hayashi-yaken/annotorch`（git init 済み。`.gitignore` と `README.md` は空ファイルとして存在するので新規作成しない）
- Python: `requires-python = ">=3.11"`
- コア依存は `pydantic>=2.7`, `numpy>=1.26`, `pillow>=10.0`, `torch>=2.2` のみ。**torchvision は使わない**
- FastAPI 系は `[server]` extra（本計画では宣言だけしてインストールしない）
- レイアウト: src レイアウト（`src/annotorch/`）
- **レイヤー依存規則（違反禁止）**: `domain` → 外部依存なし（pydanticのみ）/ `storage` → `domain` / `services` → `domain` + `storage` / `datasets` → どのレイヤーもimportしない。SQLiteに触れるのは `storage` だけ
- 環境・実行はすべて uv: `uv sync`, `uv run pytest`
- エクスポート形式バージョン: `"format_version": 1`
- preference の winner は**全レイヤーで同じ数値**: `1`（`unit.item_ids` の1番目の勝ち）/ `-1`（2番目の勝ち）/ `0`（tie）/ `null`（skip）。null はエクスポート時に除外し、規約は manifest.json の `conventions` に記録する
- ID は `uuid4().hex` の文字列
- テストは `uv run pytest tests/ -v` が常にグリーンであること。各タスク末尾でコミット
- CLI は本計画に含めない（計画2で services を呼ぶアダプタとして実装する）

---

### Task 1: プロジェクト scaffolding

**Files:**
- Modify: `.gitignore`（既存・空。エントリを追記）
- Create: `pyproject.toml`
- Create: `src/annotorch/__init__.py`
- Create: `src/annotorch/domain/__init__.py`, `src/annotorch/storage/__init__.py`, `src/annotorch/services/__init__.py`, `src/annotorch/datasets/__init__.py`（すべて空）
- Create: `tests/__init__.py`（空。テスト間の相対importのため tests をパッケージにする）
- Test: `tests/test_package.py`

**Interfaces:**
- Consumes: なし
- Produces: `annotorch.__version__: str`（`"0.1.0"`）、uv 環境、レイヤーごとの空サブパッケージ

- [ ] **Step 1: .gitignore にエントリを追記**

git init は済んでいるので不要。既存の空の `.gitignore` に以下を追記:

```
.venv/
__pycache__/
*.egg-info/
dist/
.pytest_cache/
uv.lock
.DS_Store
```

- [ ] **Step 2: 失敗するテストを書く**

`tests/test_package.py`:

```python
import annotorch


def test_version():
    assert annotorch.__version__ == "0.1.0"
```

- [ ] **Step 3: pyproject.toml とパッケージ骨格を書く**

`pyproject.toml`:

```toml
[project]
name = "annotorch"
version = "0.1.0"
description = "Annotate images/text locally and export PyTorch-ready datasets"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.7",
    "numpy>=1.26",
    "pillow>=10.0",
    "torch>=2.2",
]

[project.optional-dependencies]
server = ["fastapi>=0.110", "uvicorn>=0.29", "python-multipart>=0.0.9"]

[project.scripts]
annotorch = "annotorch.cli:main"

[dependency-groups]
dev = ["pytest>=8.0"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/annotorch"]
```

`src/annotorch/__init__.py`:

```python
__version__ = "0.1.0"
```

`domain/` `storage/` `services/` `datasets/` の各 `__init__.py` と `tests/__init__.py` は空ファイルで作成。

注意: `[project.scripts]` が `annotorch.cli:main` を指すが `cli.py` は計画2まで存在しない。`uv sync` はエントリポイントの実体を検査しないため問題ない（`annotorch` コマンドの実行だけ計画2まで失敗する）。

- [ ] **Step 4: 依存を解決してテストを実行、パスを確認**

```bash
uv sync
uv run pytest tests/ -v
```

Expected: `test_version PASSED`（torch のダウンロードで初回 `uv sync` は数分かかる）

- [ ] **Step 5: コミット**

```bash
git add .gitignore pyproject.toml src/ tests/ docs/
git commit -m "chore: scaffold annotorch package (layered src layout, uv, pytest)"
```

---

### Task 2: ドメインモデル（domain/models.py）

**Files:**
- Create: `src/annotorch/domain/models.py`
- Create: `tests/domain/__init__.py`（空）
- Test: `tests/domain/test_models.py`

**Interfaces:**
- Consumes: なし
- Produces:
  - enum: `Modality("image"|"text")`, `Presentation("single"|"pair"|"group")`, `QuestionType("hard_label"|"soft_label"|"preference"|"similarity"|"ranking"|"grouping")`
  - `VALID_QUESTIONS: dict[Presentation, set[QuestionType]]`
  - `Project(name, description="")` → `.id`, `.created_at`
  - `Item(project_id, modality, path=None, text=None, metadata={})` → `.id`
  - `TaskConfig(labels=None, similarity_mode="continuous", group_size=None, num_units=None, seed=0)`
  - `Task(project_id, name, presentation, question, config=TaskConfig())` → `.id`
  - `Unit(task_id, item_ids, position)` → `.id`
  - `Annotator(id, name)`
  - `Annotation(unit_id, annotator_id, answer)` → `.id`, `.created_at`

- [ ] **Step 1: 失敗するテストを書く**

`tests/domain/test_models.py`:

```python
import pytest
from pydantic import ValidationError

from annotorch.domain.models import (
    Item,
    Modality,
    Presentation,
    Project,
    QuestionType,
    Task,
    TaskConfig,
)


def test_project_gets_unique_id():
    a = Project(name="p1")
    b = Project(name="p2")
    assert a.id != b.id
    assert len(a.id) == 32  # uuid4().hex


def test_item_image_has_path():
    item = Item(project_id="p", modality=Modality.IMAGE, path="abc.png")
    assert item.text is None
    assert item.metadata == {}


def test_task_valid_combination():
    task = Task(
        project_id="p",
        name="classify",
        presentation=Presentation.SINGLE,
        question=QuestionType.HARD_LABEL,
        config=TaskConfig(labels=["cat", "dog"]),
    )
    assert task.config.labels == ["cat", "dog"]


def test_task_rejects_mismatched_presentation_question():
    with pytest.raises(ValidationError):
        Task(
            project_id="p",
            name="bad",
            presentation=Presentation.SINGLE,
            question=QuestionType.PREFERENCE,
            config=TaskConfig(),
        )


def test_label_task_requires_labels():
    with pytest.raises(ValidationError):
        Task(
            project_id="p",
            name="bad",
            presentation=Presentation.SINGLE,
            question=QuestionType.HARD_LABEL,
            config=TaskConfig(),
        )
```

- [ ] **Step 2: テストを実行して失敗を確認**

Run: `uv run pytest tests/domain/test_models.py -v`
Expected: FAIL（`ModuleNotFoundError: annotorch.domain.models`）

- [ ] **Step 3: 実装**

`src/annotorch/domain/models.py`:

```python
from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


def _new_id() -> str:
    return uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Modality(StrEnum):
    IMAGE = "image"
    TEXT = "text"


class Presentation(StrEnum):
    SINGLE = "single"
    PAIR = "pair"
    GROUP = "group"


class QuestionType(StrEnum):
    HARD_LABEL = "hard_label"
    SOFT_LABEL = "soft_label"
    PREFERENCE = "preference"
    SIMILARITY = "similarity"
    RANKING = "ranking"
    GROUPING = "grouping"


VALID_QUESTIONS: dict[Presentation, set[QuestionType]] = {
    Presentation.SINGLE: {QuestionType.HARD_LABEL, QuestionType.SOFT_LABEL},
    Presentation.PAIR: {QuestionType.PREFERENCE, QuestionType.SIMILARITY},
    Presentation.GROUP: {QuestionType.RANKING, QuestionType.GROUPING},
}

LABEL_QUESTIONS = {QuestionType.HARD_LABEL, QuestionType.SOFT_LABEL}


class Project(BaseModel):
    id: str = Field(default_factory=_new_id)
    name: str
    description: str = ""
    created_at: datetime = Field(default_factory=_now)


class Item(BaseModel):
    id: str = Field(default_factory=_new_id)
    project_id: str
    modality: Modality
    path: str | None = None  # image: items ディレクトリ内の相対パス
    text: str | None = None  # text: 本文そのもの
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskConfig(BaseModel):
    labels: list[str] | None = None
    similarity_mode: Literal["binary", "continuous"] = "continuous"
    group_size: int | None = None
    num_units: int | None = None
    seed: int = 0


class Task(BaseModel):
    id: str = Field(default_factory=_new_id)
    project_id: str
    name: str
    presentation: Presentation
    question: QuestionType
    config: TaskConfig = Field(default_factory=TaskConfig)

    @model_validator(mode="after")
    def _check(self) -> "Task":
        if self.question not in VALID_QUESTIONS[self.presentation]:
            raise ValueError(
                f"question {self.question} is not valid for presentation {self.presentation}"
            )
        if self.question in LABEL_QUESTIONS and not self.config.labels:
            raise ValueError(f"question {self.question} requires config.labels")
        return self


class Unit(BaseModel):
    id: str = Field(default_factory=_new_id)
    task_id: str
    item_ids: list[str]
    position: int


class Annotator(BaseModel):
    id: str = Field(default_factory=_new_id)
    name: str


class Annotation(BaseModel):
    id: str = Field(default_factory=_new_id)
    unit_id: str
    annotator_id: str
    answer: dict[str, Any]
    created_at: datetime = Field(default_factory=_now)
```

- [ ] **Step 4: テストを実行してパスを確認**

Run: `uv run pytest tests/domain/test_models.py -v`
Expected: 5 PASSED

- [ ] **Step 5: コミット**

```bash
git add src/annotorch/domain/models.py tests/domain/
git commit -m "feat: domain models (Project/Item/Task/Unit/Annotation)"
```

---

### Task 3: 回答バリデーション（domain/answers.py）

**Files:**
- Create: `src/annotorch/domain/answers.py`
- Test: `tests/domain/test_answers.py`

**Interfaces:**
- Consumes: `Task`, `Unit`, `QuestionType`（Task 2）
- Produces:
  - `AnswerValidationError(ValueError)`
  - `validate_answer(task: Task, unit: Unit, answer: dict) -> dict` — 検証済み・正規化済みの回答dictを返す（soft_label は合計1に再正規化）。不正なら `AnswerValidationError`

- [ ] **Step 1: 失敗するテストを書く**

`tests/domain/test_answers.py`:

```python
import pytest

from annotorch.domain.answers import AnswerValidationError, validate_answer
from annotorch.domain.models import Presentation, QuestionType, Task, TaskConfig, Unit


def make_task(presentation, question, **config):
    return Task(
        project_id="p",
        name="t",
        presentation=presentation,
        question=question,
        config=TaskConfig(**config),
    )


def make_unit(task, item_ids):
    return Unit(task_id=task.id, item_ids=item_ids, position=0)


class TestHardLabel:
    def setup_method(self):
        self.task = make_task(
            Presentation.SINGLE, QuestionType.HARD_LABEL, labels=["cat", "dog"]
        )
        self.unit = make_unit(self.task, ["i1"])

    def test_valid(self):
        out = validate_answer(self.task, self.unit, {"label": "cat"})
        assert out == {"label": "cat"}

    def test_unknown_label(self):
        with pytest.raises(AnswerValidationError):
            validate_answer(self.task, self.unit, {"label": "bird"})


class TestSoftLabel:
    def setup_method(self):
        self.task = make_task(
            Presentation.SINGLE, QuestionType.SOFT_LABEL, labels=["cat", "dog"]
        )
        self.unit = make_unit(self.task, ["i1"])

    def test_valid_and_renormalized(self):
        out = validate_answer(self.task, self.unit, {"dist": {"cat": 0.7, "dog": 0.3001}})
        assert abs(sum(out["dist"].values()) - 1.0) < 1e-9

    def test_sum_far_from_one(self):
        with pytest.raises(AnswerValidationError):
            validate_answer(self.task, self.unit, {"dist": {"cat": 0.5, "dog": 0.3}})

    def test_unknown_class(self):
        with pytest.raises(AnswerValidationError):
            validate_answer(self.task, self.unit, {"dist": {"bird": 1.0}})


class TestPreference:
    def setup_method(self):
        self.task = make_task(Presentation.PAIR, QuestionType.PREFERENCE, num_units=1)
        self.unit = make_unit(self.task, ["i1", "i2"])

    def test_valid(self):
        assert validate_answer(self.task, self.unit, {"winner": 1}) == {"winner": 1}
        assert validate_answer(self.task, self.unit, {"winner": -1}) == {"winner": -1}
        assert validate_answer(self.task, self.unit, {"winner": 0}) == {"winner": 0}
        assert validate_answer(self.task, self.unit, {"winner": None}) == {"winner": None}

    def test_invalid_winner(self):
        with pytest.raises(AnswerValidationError):
            validate_answer(self.task, self.unit, {"winner": 2})


class TestSimilarity:
    def test_continuous_valid(self):
        task = make_task(
            Presentation.PAIR, QuestionType.SIMILARITY, similarity_mode="continuous"
        )
        unit = make_unit(task, ["i1", "i2"])
        assert validate_answer(task, unit, {"score": 0.8}) == {"score": 0.8}

    def test_continuous_out_of_range(self):
        task = make_task(
            Presentation.PAIR, QuestionType.SIMILARITY, similarity_mode="continuous"
        )
        unit = make_unit(task, ["i1", "i2"])
        with pytest.raises(AnswerValidationError):
            validate_answer(task, unit, {"score": 1.5})

    def test_binary_requires_same(self):
        task = make_task(
            Presentation.PAIR, QuestionType.SIMILARITY, similarity_mode="binary"
        )
        unit = make_unit(task, ["i1", "i2"])
        assert validate_answer(task, unit, {"same": True}) == {"same": True}
        with pytest.raises(AnswerValidationError):
            validate_answer(task, unit, {"score": 0.5})


class TestRanking:
    def setup_method(self):
        self.task = make_task(
            Presentation.GROUP, QuestionType.RANKING, group_size=3, num_units=1
        )
        self.unit = make_unit(self.task, ["i1", "i2", "i3"])

    def test_valid_permutation(self):
        out = validate_answer(self.task, self.unit, {"order": ["i3", "i1", "i2"]})
        assert out == {"order": ["i3", "i1", "i2"]}

    def test_not_a_permutation(self):
        with pytest.raises(AnswerValidationError):
            validate_answer(self.task, self.unit, {"order": ["i1", "i1", "i2"]})
        with pytest.raises(AnswerValidationError):
            validate_answer(self.task, self.unit, {"order": ["i1", "i2"]})


class TestGrouping:
    def setup_method(self):
        self.task = make_task(
            Presentation.GROUP, QuestionType.GROUPING, group_size=4, num_units=1
        )
        self.unit = make_unit(self.task, ["i1", "i2", "i3", "i4"])

    def test_valid_partition(self):
        out = validate_answer(
            self.task, self.unit, {"groups": [["i1", "i4"], ["i2", "i3"]]}
        )
        assert out == {"groups": [["i1", "i4"], ["i2", "i3"]]}

    def test_overlap_rejected(self):
        with pytest.raises(AnswerValidationError):
            validate_answer(
                self.task, self.unit, {"groups": [["i1", "i2"], ["i2", "i3", "i4"]]}
            )

    def test_missing_item_rejected(self):
        with pytest.raises(AnswerValidationError):
            validate_answer(self.task, self.unit, {"groups": [["i1", "i2"], ["i3"]]})

    def test_empty_group_rejected(self):
        with pytest.raises(AnswerValidationError):
            validate_answer(
                self.task, self.unit, {"groups": [["i1", "i2", "i3", "i4"], []]}
            )
```

- [ ] **Step 2: テストを実行して失敗を確認**

Run: `uv run pytest tests/domain/test_answers.py -v`
Expected: FAIL（`ModuleNotFoundError: annotorch.domain.answers`）

- [ ] **Step 3: 実装**

`src/annotorch/domain/answers.py`:

```python
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ValidationError

from .models import QuestionType, Task, Unit

SUM_TOLERANCE = 1e-3


class AnswerValidationError(ValueError):
    pass


class HardLabelAnswer(BaseModel):
    label: str


class SoftLabelAnswer(BaseModel):
    dist: dict[str, float]


class PreferenceAnswer(BaseModel):
    # 1 = unit.item_ids の1番目の勝ち, -1 = 2番目の勝ち, 0 = tie, None = skip
    winner: Literal[1, -1, 0] | None


class SimilarityAnswer(BaseModel):
    score: float | None = None
    same: bool | None = None


class RankingAnswer(BaseModel):
    order: list[str]


class GroupingAnswer(BaseModel):
    groups: list[list[str]]


def _parse(model_cls: type[BaseModel], answer: dict[str, Any]) -> BaseModel:
    try:
        return model_cls.model_validate(answer, strict=False)
    except ValidationError as e:
        raise AnswerValidationError(str(e)) from e


def validate_answer(task: Task, unit: Unit, answer: dict[str, Any]) -> dict[str, Any]:
    """回答dictをタスク定義とUnitに対して検証し、正規化済みdictを返す。"""
    q = task.question

    if q == QuestionType.HARD_LABEL:
        parsed = _parse(HardLabelAnswer, answer)
        if parsed.label not in (task.config.labels or []):
            raise AnswerValidationError(f"unknown label: {parsed.label!r}")
        return {"label": parsed.label}

    if q == QuestionType.SOFT_LABEL:
        parsed = _parse(SoftLabelAnswer, answer)
        labels = set(task.config.labels or [])
        unknown = set(parsed.dist) - labels
        if unknown:
            raise AnswerValidationError(f"unknown classes in dist: {sorted(unknown)}")
        if any(v < 0 for v in parsed.dist.values()):
            raise AnswerValidationError("dist values must be non-negative")
        total = sum(parsed.dist.values())
        if abs(total - 1.0) > SUM_TOLERANCE:
            raise AnswerValidationError(f"dist must sum to 1 (got {total})")
        return {"dist": {k: v / total for k, v in parsed.dist.items()}}

    if q == QuestionType.PREFERENCE:
        parsed = _parse(PreferenceAnswer, answer)
        return {"winner": parsed.winner}

    if q == QuestionType.SIMILARITY:
        parsed = _parse(SimilarityAnswer, answer)
        if task.config.similarity_mode == "binary":
            if parsed.same is None or parsed.score is not None:
                raise AnswerValidationError("binary similarity requires {'same': bool}")
            return {"same": parsed.same}
        if parsed.score is None or parsed.same is not None:
            raise AnswerValidationError("continuous similarity requires {'score': float}")
        if not 0.0 <= parsed.score <= 1.0:
            raise AnswerValidationError(f"score must be in [0, 1] (got {parsed.score})")
        return {"score": parsed.score}

    if q == QuestionType.RANKING:
        parsed = _parse(RankingAnswer, answer)
        if sorted(parsed.order) != sorted(unit.item_ids):
            raise AnswerValidationError("order must be a permutation of the unit's items")
        return {"order": parsed.order}

    if q == QuestionType.GROUPING:
        parsed = _parse(GroupingAnswer, answer)
        if any(len(g) == 0 for g in parsed.groups):
            raise AnswerValidationError("groups must be non-empty")
        flat = [i for g in parsed.groups for i in g]
        if sorted(flat) != sorted(unit.item_ids):
            raise AnswerValidationError(
                "groups must partition the unit's items (no overlap, no missing)"
            )
        return {"groups": parsed.groups}

    raise AnswerValidationError(f"unsupported question type: {q}")
```

- [ ] **Step 4: テストを実行してパスを確認**

Run: `uv run pytest tests/domain/test_answers.py -v`
Expected: 全て PASSED

- [ ] **Step 5: コミット**

```bash
git add src/annotorch/domain/answers.py tests/domain/test_answers.py
git commit -m "feat: per-question answer validation in domain layer"
```

---

### Task 4: Unit 生成（domain/units.py）

**Files:**
- Create: `src/annotorch/domain/units.py`
- Test: `tests/domain/test_units.py`

**Interfaces:**
- Consumes: `Task`, `Unit`, `Presentation`（Task 2）
- Produces: `generate_units(task: Task, item_ids: list[str]) -> list[Unit]`
  - single: 全アイテムに1つずつ（入力順）
  - pair: `config.num_units` 必須。重複しないペアを `random.Random(config.seed)` でサンプリングし、ペア内の順序もランダム化。要求数が全ペア数を超える場合は全ペアを返す
  - group: `config.num_units` と `config.group_size`（2以上、アイテム数以下）必須。各Unitは非復元抽出
  - 入力不正は `ValueError`

- [ ] **Step 1: 失敗するテストを書く**

`tests/domain/test_units.py`:

```python
import pytest

from annotorch.domain.models import Presentation, QuestionType, Task, TaskConfig
from annotorch.domain.units import generate_units

ITEMS = [f"i{n}" for n in range(6)]


def make_task(presentation, question, **config):
    return Task(project_id="p", name="t", presentation=presentation,
                question=question, config=TaskConfig(**config))


def test_single_one_unit_per_item():
    task = make_task(Presentation.SINGLE, QuestionType.HARD_LABEL, labels=["a"])
    units = generate_units(task, ITEMS)
    assert [u.item_ids for u in units] == [[i] for i in ITEMS]
    assert [u.position for u in units] == list(range(6))


def test_pair_units_are_distinct_pairs():
    task = make_task(Presentation.PAIR, QuestionType.PREFERENCE, num_units=10, seed=42)
    units = generate_units(task, ITEMS)
    assert len(units) == 10
    seen = set()
    for u in units:
        assert len(u.item_ids) == 2
        pair = frozenset(u.item_ids)
        assert pair not in seen
        seen.add(pair)


def test_pair_deterministic_by_seed():
    task = make_task(Presentation.PAIR, QuestionType.PREFERENCE, num_units=5, seed=1)
    a = [u.item_ids for u in generate_units(task, ITEMS)]
    b = [u.item_ids for u in generate_units(task, ITEMS)]
    assert a == b


def test_pair_capped_at_all_pairs():
    task = make_task(Presentation.PAIR, QuestionType.PREFERENCE, num_units=999, seed=0)
    units = generate_units(task, ITEMS)
    assert len(units) == 15  # C(6,2)


def test_pair_requires_num_units():
    task = make_task(Presentation.PAIR, QuestionType.PREFERENCE)
    with pytest.raises(ValueError):
        generate_units(task, ITEMS)


def test_group_units():
    task = make_task(Presentation.GROUP, QuestionType.RANKING,
                     num_units=4, group_size=3, seed=7)
    units = generate_units(task, ITEMS)
    assert len(units) == 4
    for u in units:
        assert len(u.item_ids) == 3
        assert len(set(u.item_ids)) == 3


def test_group_size_too_large():
    task = make_task(Presentation.GROUP, QuestionType.RANKING,
                     num_units=1, group_size=7)
    with pytest.raises(ValueError):
        generate_units(task, ITEMS)
```

- [ ] **Step 2: テストを実行して失敗を確認**

Run: `uv run pytest tests/domain/test_units.py -v`
Expected: FAIL（`ModuleNotFoundError: annotorch.domain.units`）

- [ ] **Step 3: 実装**

`src/annotorch/domain/units.py`:

```python
from __future__ import annotations

import random
from itertools import combinations

from .models import Presentation, Task, Unit


def generate_units(task: Task, item_ids: list[str]) -> list[Unit]:
    """タスク定義に従って提示Unitを生成する（v1はランダム戦略のみ）。"""
    if task.presentation == Presentation.SINGLE:
        return [
            Unit(task_id=task.id, item_ids=[i], position=n)
            for n, i in enumerate(item_ids)
        ]

    rng = random.Random(task.config.seed)

    if task.presentation == Presentation.PAIR:
        if task.config.num_units is None:
            raise ValueError("pair task requires config.num_units")
        if len(item_ids) < 2:
            raise ValueError("pair task requires at least 2 items")
        all_pairs = list(combinations(item_ids, 2))
        n = min(task.config.num_units, len(all_pairs))
        pairs = rng.sample(all_pairs, n)
        units = []
        for pos, (a, b) in enumerate(pairs):
            ordered = [a, b] if rng.random() < 0.5 else [b, a]
            units.append(Unit(task_id=task.id, item_ids=ordered, position=pos))
        return units

    if task.presentation == Presentation.GROUP:
        size = task.config.group_size
        if task.config.num_units is None or size is None:
            raise ValueError("group task requires config.num_units and config.group_size")
        if size < 2 or size > len(item_ids):
            raise ValueError(
                f"group_size must be in [2, {len(item_ids)}] (got {size})"
            )
        return [
            Unit(task_id=task.id, item_ids=rng.sample(item_ids, size), position=pos)
            for pos in range(task.config.num_units)
        ]

    raise ValueError(f"unsupported presentation: {task.presentation}")
```

- [ ] **Step 4: テストを実行してパスを確認**

Run: `uv run pytest tests/domain/test_units.py -v`
Expected: 7 PASSED

- [ ] **Step 5: コミット**

```bash
git add src/annotorch/domain/units.py tests/domain/test_units.py
git commit -m "feat: unit generation in domain layer (single/pair/group)"
```

---

### Task 5: 永続化（storage/repository.py + storage/sqlite.py）

**Files:**
- Create: `src/annotorch/storage/repository.py`
- Create: `src/annotorch/storage/sqlite.py`
- Create: `tests/storage/__init__.py`（空）
- Test: `tests/storage/test_sqlite.py`

**Interfaces:**
- Consumes: Task 2 の全モデル
- Produces:
  - `repository.ProjectStore`（`@runtime_checkable` な Protocol）— プロジェクト1件分の永続化の抽象。以下のメソッドを持つ:
    `add_project(p)`, `get_project() -> Project`, `add_items(items)`, `list_items(project_id) -> list[Item]`, `add_task(t)`, `get_task(task_id) -> Task`, `list_tasks(project_id) -> list[Task]`, `add_units(units)`, `list_units(task_id) -> list[Unit]`, `get_default_annotator() -> Annotator`, `save_annotation(a)`, `list_annotations_for_task(task_id) -> list[Annotation]`, `close()`
  - `sqlite.SqliteStore(db_path: Path)` — ProjectStore の SQLite 実装。スキーマ作成（`meta.schema_version = "1"`）、`get_project` は存在しなければ `LookupError`、`save_annotation` は同一 `(unit_id, annotator_id)` を上書き（upsert）、`list_units` は position 順

- [ ] **Step 1: 失敗するテストを書く**

`tests/storage/test_sqlite.py`:

```python
import pytest

from annotorch.domain.models import (
    Annotation,
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
```

- [ ] **Step 2: テストを実行して失敗を確認**

Run: `uv run pytest tests/storage/test_sqlite.py -v`
Expected: FAIL（`ModuleNotFoundError`）

- [ ] **Step 3: 実装**

`src/annotorch/storage/repository.py`:

```python
from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..domain.models import Annotation, Annotator, Item, Project, Task, Unit


@runtime_checkable
class ProjectStore(Protocol):
    """プロジェクト1件分の永続化の抽象。

    SQLite実装（storage/sqlite.py）がこれを満たす。将来の複数人対応では
    RDB実装を追加し、servicesへの注入だけを差し替える。
    """

    def add_project(self, p: Project) -> None: ...
    def get_project(self) -> Project: ...
    def add_items(self, items: list[Item]) -> None: ...
    def list_items(self, project_id: str) -> list[Item]: ...
    def add_task(self, t: Task) -> None: ...
    def get_task(self, task_id: str) -> Task: ...
    def list_tasks(self, project_id: str) -> list[Task]: ...
    def add_units(self, units: list[Unit]) -> None: ...
    def list_units(self, task_id: str) -> list[Unit]: ...
    def get_default_annotator(self) -> Annotator: ...
    def save_annotation(self, a: Annotation) -> None: ...
    def list_annotations_for_task(self, task_id: str) -> list[Annotation]: ...
    def close(self) -> None: ...
```

`src/annotorch/storage/sqlite.py`:

```python
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from ..domain.models import (
    Annotation,
    Annotator,
    Item,
    Modality,
    Presentation,
    Project,
    QuestionType,
    Task,
    TaskConfig,
    Unit,
)

SCHEMA_VERSION = "1"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS items (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    modality TEXT NOT NULL,
    path TEXT,
    text TEXT,
    metadata TEXT NOT NULL DEFAULT '{}',
    seq INTEGER
);
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    name TEXT NOT NULL,
    presentation TEXT NOT NULL,
    question TEXT NOT NULL,
    config TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS units (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES tasks(id),
    position INTEGER NOT NULL,
    item_ids TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS annotators (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS annotations (
    id TEXT PRIMARY KEY,
    unit_id TEXT NOT NULL REFERENCES units(id),
    annotator_id TEXT NOT NULL REFERENCES annotators(id),
    answer TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (unit_id, annotator_id)
);
"""


class SqliteStore:
    """ProjectStore の SQLite 実装。1ファイル = 1プロジェクト。"""

    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        with self.conn:
            self.conn.executescript(_SCHEMA)
            self.conn.execute(
                "INSERT OR IGNORE INTO meta (key, value) VALUES ('schema_version', ?)",
                (SCHEMA_VERSION,),
            )

    def close(self) -> None:
        self.conn.close()

    # -- project ------------------------------------------------------------

    def add_project(self, p: Project) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO projects (id, name, description, created_at) VALUES (?, ?, ?, ?)",
                (p.id, p.name, p.description, p.created_at.isoformat()),
            )

    def get_project(self) -> Project:
        row = self.conn.execute("SELECT * FROM projects LIMIT 1").fetchone()
        if row is None:
            raise LookupError(f"no project in {self.db_path}")
        return Project(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    # -- items --------------------------------------------------------------

    def add_items(self, items: list[Item]) -> None:
        base = self.conn.execute("SELECT COALESCE(MAX(seq), -1) FROM items").fetchone()[0]
        with self.conn:
            self.conn.executemany(
                "INSERT INTO items (id, project_id, modality, path, text, metadata, seq)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    (i.id, i.project_id, i.modality.value, i.path, i.text,
                     json.dumps(i.metadata), base + 1 + n)
                    for n, i in enumerate(items)
                ],
            )

    def list_items(self, project_id: str) -> list[Item]:
        rows = self.conn.execute(
            "SELECT * FROM items WHERE project_id = ? ORDER BY seq", (project_id,)
        ).fetchall()
        return [
            Item(
                id=r["id"],
                project_id=r["project_id"],
                modality=Modality(r["modality"]),
                path=r["path"],
                text=r["text"],
                metadata=json.loads(r["metadata"]),
            )
            for r in rows
        ]

    # -- tasks --------------------------------------------------------------

    def add_task(self, t: Task) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO tasks (id, project_id, name, presentation, question, config)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (t.id, t.project_id, t.name, t.presentation.value, t.question.value,
                 t.config.model_dump_json()),
            )

    def _row_to_task(self, r: sqlite3.Row) -> Task:
        return Task(
            id=r["id"],
            project_id=r["project_id"],
            name=r["name"],
            presentation=Presentation(r["presentation"]),
            question=QuestionType(r["question"]),
            config=TaskConfig.model_validate_json(r["config"]),
        )

    def get_task(self, task_id: str) -> Task:
        row = self.conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            raise LookupError(f"no task {task_id}")
        return self._row_to_task(row)

    def list_tasks(self, project_id: str) -> list[Task]:
        rows = self.conn.execute(
            "SELECT * FROM tasks WHERE project_id = ? ORDER BY rowid", (project_id,)
        ).fetchall()
        return [self._row_to_task(r) for r in rows]

    # -- units --------------------------------------------------------------

    def add_units(self, units: list[Unit]) -> None:
        with self.conn:
            self.conn.executemany(
                "INSERT INTO units (id, task_id, position, item_ids) VALUES (?, ?, ?, ?)",
                [(u.id, u.task_id, u.position, json.dumps(u.item_ids)) for u in units],
            )

    def list_units(self, task_id: str) -> list[Unit]:
        rows = self.conn.execute(
            "SELECT * FROM units WHERE task_id = ? ORDER BY position", (task_id,)
        ).fetchall()
        return [
            Unit(id=r["id"], task_id=r["task_id"], item_ids=json.loads(r["item_ids"]),
                 position=r["position"])
            for r in rows
        ]

    # -- annotators / annotations --------------------------------------------

    def get_default_annotator(self) -> Annotator:
        with self.conn:
            self.conn.execute(
                "INSERT OR IGNORE INTO annotators (id, name) VALUES ('default', 'default')"
            )
        row = self.conn.execute(
            "SELECT * FROM annotators WHERE id = 'default'"
        ).fetchone()
        return Annotator(id=row["id"], name=row["name"])

    def save_annotation(self, a: Annotation) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO annotations (id, unit_id, annotator_id, answer, created_at)"
                " VALUES (?, ?, ?, ?, ?)"
                " ON CONFLICT (unit_id, annotator_id) DO UPDATE SET"
                "   answer = excluded.answer, created_at = excluded.created_at",
                (a.id, a.unit_id, a.annotator_id, json.dumps(a.answer),
                 a.created_at.isoformat()),
            )

    def list_annotations_for_task(self, task_id: str) -> list[Annotation]:
        rows = self.conn.execute(
            "SELECT a.* FROM annotations a JOIN units u ON a.unit_id = u.id"
            " WHERE u.task_id = ? ORDER BY u.position",
            (task_id,),
        ).fetchall()
        return [
            Annotation(
                id=r["id"],
                unit_id=r["unit_id"],
                annotator_id=r["annotator_id"],
                answer=json.loads(r["answer"]),
                created_at=datetime.fromisoformat(r["created_at"]),
            )
            for r in rows
        ]
```

- [ ] **Step 4: テストを実行してパスを確認**

Run: `uv run pytest tests/storage/test_sqlite.py -v`
Expected: 7 PASSED

- [ ] **Step 5: コミット**

```bash
git add src/annotorch/storage/ tests/storage/
git commit -m "feat: ProjectStore protocol and SQLite implementation"
```

---

### Task 6: ワークスペース（storage/workspace.py）

**Files:**
- Create: `src/annotorch/storage/workspace.py`
- Test: `tests/storage/test_workspace.py`

**Interfaces:**
- Consumes: `SqliteStore`（Task 5）、`Project`（Task 2）
- Produces: `Workspace` クラス — ディレクトリレイアウト `root/projects/<project_id>/{project.db, items/}` の管理:
  - `Workspace(root: Path)`
  - `create_project(name: str, description: str = "") -> Project`
  - `list_projects() -> list[Project]`
  - `delete_project(project_id: str) -> None`（無ければ `LookupError`）
  - `storage(project_id: str) -> SqliteStore`（存在しなければ `LookupError`）
  - `open(project_id: str)` — コンテキストマネージャ。`ProjectStore` を yield し、確実に close する（services はこれを使う）
  - `items_dir(project_id: str) -> Path`（作成して返す）

- [ ] **Step 1: 失敗するテストを書く**

`tests/storage/test_workspace.py`:

```python
import pytest

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
```

- [ ] **Step 2: テストを実行して失敗を確認**

Run: `uv run pytest tests/storage/test_workspace.py -v`
Expected: FAIL（`ModuleNotFoundError`）

- [ ] **Step 3: 実装**

`src/annotorch/storage/workspace.py`:

```python
from __future__ import annotations

import shutil
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from ..domain.models import Project
from .repository import ProjectStore
from .sqlite import SqliteStore


class Workspace:
    """root/projects/<project_id>/{project.db, items/} のレイアウトを管理する。"""

    def __init__(self, root: Path | str):
        self.root = Path(root)

    def _project_dir(self, project_id: str) -> Path:
        return self.root / "projects" / project_id

    def create_project(self, name: str, description: str = "") -> Project:
        project = Project(name=name, description=description)
        store = SqliteStore(self._project_dir(project.id) / "project.db")
        try:
            store.add_project(project)
        finally:
            store.close()
        self.items_dir(project.id)
        return project

    def list_projects(self) -> list[Project]:
        projects_dir = self.root / "projects"
        if not projects_dir.is_dir():
            return []
        out: list[Project] = []
        for db in sorted(projects_dir.glob("*/project.db")):
            store = SqliteStore(db)
            try:
                out.append(store.get_project())
            finally:
                store.close()
        return out

    def delete_project(self, project_id: str) -> None:
        d = self._project_dir(project_id)
        if not d.is_dir():
            raise LookupError(f"no project {project_id} under {self.root}")
        shutil.rmtree(d)

    def storage(self, project_id: str) -> SqliteStore:
        db = self._project_dir(project_id) / "project.db"
        if not db.exists():
            raise LookupError(f"no project {project_id} under {self.root}")
        return SqliteStore(db)

    @contextmanager
    def open(self, project_id: str) -> Iterator[ProjectStore]:
        store = self.storage(project_id)
        try:
            yield store
        finally:
            store.close()

    def items_dir(self, project_id: str) -> Path:
        d = self._project_dir(project_id) / "items"
        d.mkdir(parents=True, exist_ok=True)
        return d
```

- [ ] **Step 4: テストを実行してパスを確認**

Run: `uv run pytest tests/storage/test_workspace.py -v`
Expected: 5 PASSED

- [ ] **Step 5: コミット**

```bash
git add src/annotorch/storage/workspace.py tests/storage/test_workspace.py
git commit -m "feat: workspace directory layout with managed store lifecycle"
```

---

### Task 7: ProjectService（services/projects.py）

**Files:**
- Create: `src/annotorch/services/projects.py`
- Create: `tests/services/__init__.py`（空）
- Test: `tests/services/test_projects.py`

**Interfaces:**
- Consumes: `Workspace`（Task 6）、`Item`, `Modality`, `Project`（Task 2）
- Produces:
  - `SkippedFile(source, reason)`、`ImportReport(imported: int, skipped: list[SkippedFile])`
  - `ProjectService(workspace)`:
    - `create(name, description="") -> Project` / `list() -> list[Project]` / `delete(project_id)`
    - `list_items(project_id) -> list[Item]`
    - `item_file_path(project_id, item_id) -> Path`（ファイルを持たない/未知のitemは `LookupError`）
    - `import_images(project_id, source_dir: Path) -> ImportReport` — 再帰走査、対応拡張子かつ Pillow で開ける画像だけを items_dir にコピーして登録。それ以外は理由付きで skipped
    - `import_texts_jsonl(project_id, jsonl_path) -> ImportReport`（各行 `{"text": str, ...}`。text 以外は metadata へ）
    - `import_texts_csv(project_id, csv_path) -> ImportReport`（`text` 列必須）

- [ ] **Step 1: 失敗するテストを書く**

`tests/services/test_projects.py`:

```python
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
```

- [ ] **Step 2: テストを実行して失敗を確認**

Run: `uv run pytest tests/services/test_projects.py -v`
Expected: FAIL（`ModuleNotFoundError`）

- [ ] **Step 3: 実装**

`src/annotorch/services/projects.py`:

```python
from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

from PIL import Image
from pydantic import BaseModel, Field

from ..domain.models import Item, Modality, Project
from ..storage.workspace import Workspace

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}


class SkippedFile(BaseModel):
    source: str
    reason: str


class ImportReport(BaseModel):
    imported: int = 0
    skipped: list[SkippedFile] = Field(default_factory=list)


class ProjectService:
    """プロジェクト管理とアイテム取り込みのユースケース。"""

    def __init__(self, workspace: Workspace):
        self.ws = workspace

    def create(self, name: str, description: str = "") -> Project:
        return self.ws.create_project(name, description)

    def list(self) -> list[Project]:
        return self.ws.list_projects()

    def delete(self, project_id: str) -> None:
        self.ws.delete_project(project_id)

    def list_items(self, project_id: str) -> list[Item]:
        with self.ws.open(project_id) as store:
            return store.list_items(project_id)

    def item_file_path(self, project_id: str, item_id: str) -> Path:
        with self.ws.open(project_id) as store:
            match = [i for i in store.list_items(project_id) if i.id == item_id]
        if not match or match[0].path is None:
            raise LookupError(f"no file for item {item_id}")
        return self.ws.items_dir(project_id) / match[0].path

    def import_images(self, project_id: str, source_dir: Path) -> ImportReport:
        report = ImportReport()
        items: list[Item] = []
        items_dir = self.ws.items_dir(project_id)
        for path in sorted(p for p in Path(source_dir).rglob("*") if p.is_file()):
            ext = path.suffix.lower()
            if ext not in IMAGE_EXTENSIONS:
                report.skipped.append(
                    SkippedFile(source=str(path), reason=f"unsupported extension {ext!r}")
                )
                continue
            try:
                with Image.open(path) as img:
                    img.verify()
            except Exception as e:
                report.skipped.append(
                    SkippedFile(source=str(path), reason=f"unreadable image: {e}")
                )
                continue
            item = Item(project_id=project_id, modality=Modality.IMAGE,
                        metadata={"source": str(path)})
            item.path = f"{item.id}{ext}"
            shutil.copy2(path, items_dir / item.path)
            items.append(item)
        if items:
            with self.ws.open(project_id) as store:
                store.add_items(items)
        report.imported = len(items)
        return report

    def import_texts_jsonl(self, project_id: str, jsonl_path: Path) -> ImportReport:
        report = ImportReport()
        items: list[Item] = []
        for n, line in enumerate(Path(jsonl_path).read_text().splitlines(), start=1):
            if not line.strip():
                continue
            source = f"{jsonl_path}:{n}"
            try:
                record = json.loads(line)
            except json.JSONDecodeError as e:
                report.skipped.append(
                    SkippedFile(source=source, reason=f"invalid JSON: {e}")
                )
                continue
            text = record.pop("text", None) if isinstance(record, dict) else None
            if not isinstance(text, str):
                report.skipped.append(
                    SkippedFile(source=source, reason="missing string 'text' field")
                )
                continue
            items.append(Item(project_id=project_id, modality=Modality.TEXT,
                              text=text, metadata=record))
        if items:
            with self.ws.open(project_id) as store:
                store.add_items(items)
        report.imported = len(items)
        return report

    def import_texts_csv(self, project_id: str, csv_path: Path) -> ImportReport:
        report = ImportReport()
        with open(csv_path, newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None or "text" not in reader.fieldnames:
                report.skipped.append(
                    SkippedFile(source=str(csv_path), reason="missing 'text' column")
                )
                return report
            items = []
            for row in reader:
                text = row.pop("text")
                items.append(Item(project_id=project_id, modality=Modality.TEXT,
                                  text=text, metadata=row))
        if items:
            with self.ws.open(project_id) as store:
                store.add_items(items)
        report.imported = len(items)
        return report
```

- [ ] **Step 4: テストを実行してパスを確認**

Run: `uv run pytest tests/services/test_projects.py -v`
Expected: 7 PASSED

- [ ] **Step 5: コミット**

```bash
git add src/annotorch/services/projects.py tests/services/
git commit -m "feat: ProjectService (project management and item importing)"
```

---

### Task 8: TaskService（services/tasks.py）

**Files:**
- Create: `src/annotorch/services/tasks.py`
- Test: `tests/services/test_tasks.py`

**Interfaces:**
- Consumes: `validate_answer` / `generate_units`（domain）、`Workspace`
- Produces:
  - `TaskWithProgress(Task)` — `total_units: int`, `answered_units: int` を追加
  - `UnitDetail(id, position, items: list[Item], answer: dict | None)`
  - `TaskService(workspace)`:
    - `create_task(project_id, name, presentation, question, config) -> tuple[Task, int]`
      （不正な組み合わせ・生成不能は `ValueError`。pydantic ValidationError も ValueError に包む）
    - `list_tasks_with_progress(project_id) -> list[TaskWithProgress]`
    - `list_units(project_id, task_id) -> list[UnitDetail]`（position順、既存回答入り。task未知は `LookupError`）
    - `save_answer(project_id, task_id, unit_id, answer: dict) -> dict`
      （検証は `validate_answer`。unit未知は `LookupError`、不正回答は `AnswerValidationError`）

- [ ] **Step 1: 失敗するテストを書く**

`tests/services/test_tasks.py`:

```python
import pytest
from PIL import Image

from annotorch.domain.answers import AnswerValidationError
from annotorch.domain.models import Presentation, QuestionType, TaskConfig
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


def test_create_task_invalid_combination_raises(env):
    project, tasks = env
    with pytest.raises(ValueError):
        tasks.create_task(project.id, "bad", Presentation.SINGLE,
                          QuestionType.PREFERENCE, TaskConfig())


def test_create_pair_task_without_num_units_raises(env):
    project, tasks = env
    with pytest.raises(ValueError):
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
    with pytest.raises(LookupError):
        tasks.save_answer(project.id, task.id, "nope", {"label": "cat"})
```

- [ ] **Step 2: テストを実行して失敗を確認**

Run: `uv run pytest tests/services/test_tasks.py -v`
Expected: FAIL（`ModuleNotFoundError`）

- [ ] **Step 3: 実装**

`src/annotorch/services/tasks.py`:

```python
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ValidationError

from ..domain.answers import validate_answer
from ..domain.models import (
    Annotation,
    Item,
    Presentation,
    QuestionType,
    Task,
    TaskConfig,
)
from ..domain.units import generate_units
from ..storage.workspace import Workspace


class TaskWithProgress(Task):
    total_units: int
    answered_units: int


class UnitDetail(BaseModel):
    id: str
    position: int
    items: list[Item]
    answer: dict[str, Any] | None


class TaskService:
    """タスク定義・Unit提示・回答保存のユースケース。"""

    def __init__(self, workspace: Workspace):
        self.ws = workspace

    def create_task(self, project_id: str, name: str, presentation: Presentation,
                    question: QuestionType, config: TaskConfig) -> tuple[Task, int]:
        try:
            task = Task(project_id=project_id, name=name, presentation=presentation,
                        question=question, config=config)
        except ValidationError as e:
            raise ValueError(str(e)) from e
        with self.ws.open(project_id) as store:
            item_ids = [i.id for i in store.list_items(project_id)]
            units = generate_units(task, item_ids)  # 設定不正は ValueError
            store.add_task(task)
            store.add_units(units)
        return task, len(units)

    def list_tasks_with_progress(self, project_id: str) -> list[TaskWithProgress]:
        with self.ws.open(project_id) as store:
            out = []
            for task in store.list_tasks(project_id):
                units = store.list_units(task.id)
                anns = store.list_annotations_for_task(task.id)
                out.append(TaskWithProgress(
                    **task.model_dump(),
                    total_units=len(units),
                    answered_units=len({a.unit_id for a in anns}),
                ))
            return out

    def list_units(self, project_id: str, task_id: str) -> list[UnitDetail]:
        with self.ws.open(project_id) as store:
            store.get_task(task_id)  # 未知の task は LookupError
            items = {i.id: i for i in store.list_items(project_id)}
            answers = {a.unit_id: a.answer
                       for a in store.list_annotations_for_task(task_id)}
            return [
                UnitDetail(id=u.id, position=u.position,
                           items=[items[i] for i in u.item_ids],
                           answer=answers.get(u.id))
                for u in store.list_units(task_id)
            ]

    def save_answer(self, project_id: str, task_id: str, unit_id: str,
                    answer: dict[str, Any]) -> dict[str, Any]:
        with self.ws.open(project_id) as store:
            task = store.get_task(task_id)
            unit = next((u for u in store.list_units(task_id) if u.id == unit_id), None)
            if unit is None:
                raise LookupError(f"no unit {unit_id}")
            validated = validate_answer(task, unit, answer)
            annotator = store.get_default_annotator()
            store.save_annotation(Annotation(unit_id=unit_id,
                                             annotator_id=annotator.id,
                                             answer=validated))
            return validated
```

- [ ] **Step 4: テストを実行してパスを確認**

Run: `uv run pytest tests/services/test_tasks.py -v`
Expected: 6 PASSED

- [ ] **Step 5: コミット**

```bash
git add src/annotorch/services/tasks.py tests/services/test_tasks.py
git commit -m "feat: TaskService (task creation, progress, unit listing, answer saving)"
```

---

### Task 9: ExportService（services/exports.py）

**Files:**
- Create: `src/annotorch/services/exports.py`
- Test: `tests/services/test_exports.py`

**Interfaces:**
- Consumes: `ProjectStore`（storage）、`Workspace`、`QuestionType`、`annotorch.__version__`
- Produces:
  - `ExportResult(output_dir: Path, num_rows, num_unanswered_units, num_skipped, split_counts)`
  - `ExportService(workspace)`:
    - `export(project_id, task_id, output_dir: Path, splits: dict[str, float] | None = None, seed: int = 0) -> ExportResult`
    - splits の合計が1でなければ `ValueError`、出力先既存は `FileExistsError`
- 出力レイアウト（スペック準拠 + items.jsonl を常設のインデックスとして追加）:
  - `manifest.json` — `format_version`, `generator`, `task {name, presentation, question}`, `classes`（ラベル系以外は null）, `modality`（"image"/"text"/"mixed"）, `aggregation: "raw"`, `conventions`（preference では winner の意味を記録）, `seed`, `splits`（split名→行数）
  - `items.jsonl` — 参照される Item のインデックス。画像: `{"id", "modality": "image", "file": "items/<id>.<ext>", "metadata"}`、テキスト: `{"id", "modality": "text", "text", "metadata"}`
  - `items/` — 画像ファイルのコピー
  - `annotations.jsonl` — 1行 = 1 Annotation: `{"unit_id", "item_ids", "answer", "annotator_id", "split"}`
- 挙動:
  - 未回答 Unit は除外し `num_unanswered_units` で報告
  - preference の `winner: null`（skip）回答は除外し `num_skipped` で報告
  - split は Unit 単位で割り当て（`random.Random(seed)` でシャッフル→比率分割）。`splits=None` なら全行 `"train"`
  - 一時ディレクトリ `.<name>.tmp` に書き切ってから `rename` で確定。失敗時は tmp を削除

- [ ] **Step 1: 失敗するテストを書く**

`tests/services/test_exports.py`:

```python
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
```

- [ ] **Step 2: テストを実行して失敗を確認**

Run: `uv run pytest tests/services/test_exports.py -v`
Expected: FAIL（`ModuleNotFoundError`）

- [ ] **Step 3: 実装**

`src/annotorch/services/exports.py`:

```python
from __future__ import annotations

import json
import random
import shutil
from pathlib import Path

from pydantic import BaseModel, Field

from .. import __version__
from ..domain.models import QuestionType
from ..storage.repository import ProjectStore
from ..storage.workspace import Workspace

FORMAT_VERSION = 1


class ExportResult(BaseModel):
    output_dir: Path
    num_rows: int
    num_unanswered_units: int
    num_skipped: int
    split_counts: dict[str, int] = Field(default_factory=dict)


class ExportService:
    """アノテーション済みタスクの自己完結データセットへの書き出し。"""

    def __init__(self, workspace: Workspace):
        self.ws = workspace

    def export(self, project_id: str, task_id: str, output_dir: Path,
               splits: dict[str, float] | None = None, seed: int = 0) -> ExportResult:
        if splits is not None:
            if not splits:
                raise ValueError("splits must not be empty")
            total = sum(splits.values())
            if abs(total - 1.0) > 1e-3:
                raise ValueError(f"split fractions must sum to 1 (got {total})")
        with self.ws.open(project_id) as store:
            return _export(store, task_id, self.ws.items_dir(project_id),
                           Path(output_dir), splits, seed)


def _assign_splits(
    unit_ids: list[str], splits: dict[str, float] | None, seed: int
) -> dict[str, str]:
    if not splits:
        return {u: "train" for u in unit_ids}
    shuffled = list(unit_ids)
    random.Random(seed).shuffle(shuffled)
    assignment: dict[str, str] = {}
    names = list(splits)
    n = len(shuffled)
    start = 0
    cumulative = 0.0
    for k, name in enumerate(names):
        cumulative += splits[name]
        end = n if k == len(names) - 1 else round(cumulative * n)
        for u in shuffled[start:end]:
            assignment[u] = name
        start = end
    return assignment


def _export(store: ProjectStore, task_id: str, items_dir: Path,
            output_dir: Path, splits: dict[str, float] | None,
            seed: int) -> ExportResult:
    task = store.get_task(task_id)
    units = {u.id: u for u in store.list_units(task_id)}
    annotations = store.list_annotations_for_task(task_id)

    num_skipped = 0
    rows_source = []
    answered_unit_ids: list[str] = []
    for a in annotations:
        if task.question == QuestionType.PREFERENCE and a.answer.get("winner") is None:
            num_skipped += 1
            continue
        rows_source.append(a)
        if a.unit_id not in answered_unit_ids:
            answered_unit_ids.append(a.unit_id)
    num_unanswered = len(units) - len({a.unit_id for a in annotations})

    split_of = _assign_splits(answered_unit_ids, splits, seed)

    referenced_item_ids: list[str] = []
    for a in rows_source:
        for item_id in units[a.unit_id].item_ids:
            if item_id not in referenced_item_ids:
                referenced_item_ids.append(item_id)
    all_items = {i.id: i for i in store.list_items(task.project_id)}

    if output_dir.exists():
        raise FileExistsError(f"output already exists: {output_dir}")
    tmp = output_dir.parent / f".{output_dir.name}.tmp"
    if tmp.exists():
        shutil.rmtree(tmp)

    try:
        (tmp / "items").mkdir(parents=True)

        modalities = set()
        with open(tmp / "items.jsonl", "w") as f:
            for item_id in referenced_item_ids:
                item = all_items[item_id]
                modalities.add(item.modality.value)
                if item.path is not None:
                    src = items_dir / item.path
                    if not src.exists():
                        raise FileNotFoundError(f"item file missing: {src}")
                    shutil.copy2(src, tmp / "items" / item.path)
                    record = {"id": item.id, "modality": item.modality.value,
                              "file": f"items/{item.path}", "metadata": item.metadata}
                else:
                    record = {"id": item.id, "modality": item.modality.value,
                              "text": item.text, "metadata": item.metadata}
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

        split_counts: dict[str, int] = {}
        with open(tmp / "annotations.jsonl", "w") as f:
            for a in rows_source:
                split = split_of[a.unit_id]
                split_counts[split] = split_counts.get(split, 0) + 1
                row = {
                    "unit_id": a.unit_id,
                    "item_ids": units[a.unit_id].item_ids,
                    "answer": a.answer,
                    "annotator_id": a.annotator_id,
                    "split": split,
                }
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

        modality = modalities.pop() if len(modalities) == 1 else (
            "mixed" if modalities else "empty"
        )
        manifest = {
            "format_version": FORMAT_VERSION,
            "generator": f"annotorch {__version__}",
            "task": {"name": task.name, "presentation": task.presentation.value,
                     "question": task.question.value},
            "classes": task.config.labels,
            "modality": modality,
            "aggregation": "raw",
            "conventions": (
                {"preference_winner":
                 "1 = first item in item_ids wins, -1 = second, 0 = tie"}
                if task.question == QuestionType.PREFERENCE else {}
            ),
            "seed": seed,
            "splits": split_counts,
        }
        (tmp / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2)
        )

        tmp.rename(output_dir)
    except BaseException:
        if tmp.exists():
            shutil.rmtree(tmp)
        raise

    return ExportResult(
        output_dir=output_dir,
        num_rows=len(rows_source),
        num_unanswered_units=num_unanswered,
        num_skipped=num_skipped,
        split_counts=split_counts,
    )
```

- [ ] **Step 4: テストを実行してパスを確認**

Run: `uv run pytest tests/services/test_exports.py -v`
Expected: 5 PASSED

- [ ] **Step 5: コミット**

```bash
git add src/annotorch/services/exports.py tests/services/test_exports.py
git commit -m "feat: ExportService (atomic self-contained dataset export)"
```

---

### Task 10: Dataset 読み込み基盤 + 分類系（datasets/base.py, classification.py, load()）

**Files:**
- Create: `src/annotorch/datasets/base.py`
- Create: `src/annotorch/datasets/classification.py`
- Modify: `src/annotorch/datasets/__init__.py`
- Create: `tests/datasets/__init__.py`（空）
- Test: `tests/datasets/test_classification.py`

**Interfaces:**
- Consumes: Task 9 のエクスポート形式（**ファイルのみ。他レイヤーを import しない**）
- Produces:
  - `annotorch.datasets.load(root, split="train", transform=None)` — manifest の question を見て適切な Dataset を返す。split が manifest の splits に無ければ `ValueError`
  - `base.AnnotorchDataset(torch.utils.data.Dataset)` — 共通属性 `manifest: dict`、メソッド `_load_obj(item_id)`（画像は `PIL.Image`（RGB変換）、テキストは `str` を返し、transform があれば適用）、`__len__`
  - `classification.HardLabelDataset` — `ds[i] -> (obj, label_idx: int)`、`ds.classes: list[str]`、`ds.class_to_idx: dict[str, int]`
  - `classification.SoftLabelDataset` — `ds[i] -> (obj, dist: torch.FloatTensor(num_classes,))`、`ds.classes`

- [ ] **Step 1: 失敗するテストを書く**

`tests/datasets/test_classification.py`:

```python
import json

import numpy as np
import pytest
import torch
from PIL import Image
from torch.utils.data import DataLoader

from annotorch.datasets import load


def write_dataset(root, question, classes, rows, image_ids=(), text_items=()):
    """エクスポート形式のデータセットを直接書き出すテストヘルパ。"""
    (root / "items").mkdir(parents=True)
    with open(root / "items.jsonl", "w") as f:
        for n, item_id in enumerate(image_ids):
            fname = f"items/{item_id}.png"
            Image.new("RGB", (8, 8), (n * 30 % 256, 0, 0)).save(root / fname)
            f.write(json.dumps({"id": item_id, "modality": "image",
                                "file": fname, "metadata": {}}) + "\n")
        for item_id, text in text_items:
            f.write(json.dumps({"id": item_id, "modality": "text",
                                "text": text, "metadata": {}}) + "\n")
    split_counts = {}
    with open(root / "annotations.jsonl", "w") as f:
        for row in rows:
            split_counts[row["split"]] = split_counts.get(row["split"], 0) + 1
            f.write(json.dumps(row) + "\n")
    manifest = {
        "format_version": 1,
        "generator": "test",
        "task": {"name": "t", "presentation": "single", "question": question},
        "classes": classes,
        "modality": "image" if image_ids else "text",
        "aggregation": "raw",
        "conventions": {},
        "seed": 0,
        "splits": split_counts,
    }
    (root / "manifest.json").write_text(json.dumps(manifest))


TO_TENSOR = lambda img: torch.from_numpy(np.array(img, dtype=np.float32) / 255.0)


def hard_rows(image_ids, labels):
    return [
        {"unit_id": f"u{n}", "item_ids": [i], "answer": {"label": lb},
         "annotator_id": "default", "split": "train"}
        for n, (i, lb) in enumerate(zip(image_ids, labels))
    ]


def test_hard_label_dataset(tmp_path):
    ids = ["a", "b", "c"]
    write_dataset(tmp_path, "hard_label", ["cat", "dog"],
                  hard_rows(ids, ["cat", "dog", "cat"]), image_ids=ids)
    ds = load(tmp_path, split="train")
    assert len(ds) == 3
    assert ds.classes == ["cat", "dog"]
    obj, label = ds[1]
    assert isinstance(obj, Image.Image)
    assert label == 1


def test_hard_label_with_transform_and_dataloader(tmp_path):
    ids = ["a", "b", "c"]
    write_dataset(tmp_path, "hard_label", ["cat", "dog"],
                  hard_rows(ids, ["cat", "dog", "cat"]), image_ids=ids)
    ds = load(tmp_path, split="train", transform=TO_TENSOR)
    batch_x, batch_y = next(iter(DataLoader(ds, batch_size=3)))
    assert batch_x.shape == (3, 8, 8, 3)
    assert batch_y.tolist() == [0, 1, 0]


def test_soft_label_dataset(tmp_path):
    ids = ["a", "b"]
    rows = [
        {"unit_id": "u0", "item_ids": ["a"], "answer": {"dist": {"cat": 0.7, "dog": 0.3}},
         "annotator_id": "default", "split": "train"},
        {"unit_id": "u1", "item_ids": ["b"], "answer": {"dist": {"dog": 1.0}},
         "annotator_id": "default", "split": "train"},
    ]
    write_dataset(tmp_path, "soft_label", ["cat", "dog"], rows, image_ids=ids)
    ds = load(tmp_path, split="train")
    _, dist = ds[0]
    assert isinstance(dist, torch.Tensor)
    assert dist.dtype == torch.float32
    assert torch.allclose(dist, torch.tensor([0.7, 0.3]))
    _, dist1 = ds[1]
    assert torch.allclose(dist1, torch.tensor([0.0, 1.0]))


def test_text_modality(tmp_path):
    rows = hard_rows(["t1"], ["cat"])
    write_dataset(tmp_path, "hard_label", ["cat", "dog"], rows,
                  text_items=[("t1", "hello world")])
    ds = load(tmp_path, split="train")
    obj, label = ds[0]
    assert obj == "hello world"
    assert label == 0


def test_unknown_split_raises(tmp_path):
    ids = ["a"]
    write_dataset(tmp_path, "hard_label", ["cat", "dog"],
                  hard_rows(ids, ["cat"]), image_ids=ids)
    with pytest.raises(ValueError):
        load(tmp_path, split="test")
```

- [ ] **Step 2: テストを実行して失敗を確認**

Run: `uv run pytest tests/datasets/test_classification.py -v`
Expected: FAIL（`ImportError: cannot import name 'load'`）

- [ ] **Step 3: 実装**

`src/annotorch/datasets/base.py`:

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from PIL import Image
from torch.utils.data import Dataset


def read_manifest(root: Path | str) -> dict:
    manifest_path = Path(root) / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"not an annotorch dataset (no manifest.json): {root}")
    return json.loads(manifest_path.read_text())


class AnnotorchDataset(Dataset):
    """エクスポート済みデータセットの共通読み込み基盤。"""

    def __init__(self, root: Path | str, split: str = "train",
                 transform: Callable | None = None):
        self.root = Path(root)
        self.manifest = read_manifest(self.root)
        available = self.manifest.get("splits", {})
        if split not in available:
            raise ValueError(
                f"split {split!r} not in dataset (available: {sorted(available)})"
            )
        self.split = split
        self.transform = transform
        self._items: dict[str, dict] = {}
        for line in (self.root / "items.jsonl").read_text().splitlines():
            record = json.loads(line)
            self._items[record["id"]] = record
        self.rows: list[dict] = [
            row
            for line in (self.root / "annotations.jsonl").read_text().splitlines()
            if (row := json.loads(line))["split"] == split
        ]

    def _load_obj(self, item_id: str) -> Any:
        record = self._items[item_id]
        if "file" in record:
            with Image.open(self.root / record["file"]) as img:
                obj: Any = img.convert("RGB")
        else:
            obj = record["text"]
        if self.transform is not None:
            obj = self.transform(obj)
        return obj

    def __len__(self) -> int:
        return len(self.rows)
```

`src/annotorch/datasets/classification.py`:

```python
from __future__ import annotations

import torch

from .base import AnnotorchDataset


class _LabeledDataset(AnnotorchDataset):
    def __init__(self, root, split="train", transform=None):
        super().__init__(root, split=split, transform=transform)
        self.classes: list[str] = list(self.manifest["classes"])
        self.class_to_idx: dict[str, int] = {c: n for n, c in enumerate(self.classes)}


class HardLabelDataset(_LabeledDataset):
    def __getitem__(self, index: int):
        row = self.rows[index]
        obj = self._load_obj(row["item_ids"][0])
        return obj, self.class_to_idx[row["answer"]["label"]]


class SoftLabelDataset(_LabeledDataset):
    def __getitem__(self, index: int):
        row = self.rows[index]
        obj = self._load_obj(row["item_ids"][0])
        dist = row["answer"]["dist"]
        target = torch.tensor(
            [dist.get(c, 0.0) for c in self.classes], dtype=torch.float32
        )
        return obj, target
```

`src/annotorch/datasets/__init__.py`（全置換）:

```python
from __future__ import annotations

from pathlib import Path
from typing import Callable

from .base import AnnotorchDataset, read_manifest


def load(root: Path | str, split: str = "train",
         transform: Callable | None = None) -> AnnotorchDataset:
    """エクスポート済み annotorch データセットを読み込む。

    manifest の question に応じた Dataset サブクラスを返す。
    """
    question = read_manifest(root)["task"]["question"]
    if question == "hard_label":
        from .classification import HardLabelDataset as cls
    elif question == "soft_label":
        from .classification import SoftLabelDataset as cls
    else:
        raise ValueError(f"unsupported question type: {question}")
    return cls(root, split=split, transform=transform)
```

（`else` 分岐は Task 11 / 12 で pair / group に置き換える）

- [ ] **Step 4: テストを実行してパスを確認**

Run: `uv run pytest tests/datasets/test_classification.py -v`
Expected: 5 PASSED

- [ ] **Step 5: コミット**

```bash
git add src/annotorch/datasets/ tests/datasets/
git commit -m "feat: dataset loading base + hard/soft label datasets"
```

---

### Task 11: ペア系 Dataset（datasets/pair.py）

**Files:**
- Create: `src/annotorch/datasets/pair.py`
- Modify: `src/annotorch/datasets/__init__.py`（load の分岐追加）
- Test: `tests/datasets/test_pair.py`

**Interfaces:**
- Consumes: `AnnotorchDataset`（Task 10）
- Produces:
  - `PreferenceDataset` — `ds[i] -> ((obj_a, obj_b), winner: int)`。保存値をそのまま返す（**1 = 1番目の勝ち, -1 = 2番目, 0 = tie**。skip=null はエクスポート時に除外済み）
  - `SimilarityDataset` — `ds[i] -> ((obj_a, obj_b), score: float)`。binary の場合 `same: true -> 1.0 / false -> 0.0`

- [ ] **Step 1: 失敗するテストを書く**

`tests/datasets/test_pair.py`:

```python
import numpy as np
import torch
from torch.utils.data import DataLoader

from annotorch.datasets import load

from .test_classification import write_dataset

TO_TENSOR = lambda img: torch.from_numpy(np.array(img, dtype=np.float32) / 255.0)


def pair_rows(answers):
    return [
        {"unit_id": f"u{n}", "item_ids": ["a", "b"], "answer": ans,
         "annotator_id": "default", "split": "train"}
        for n, ans in enumerate(answers)
    ]


def patch_manifest(root, question):
    import json
    manifest = json.loads((root / "manifest.json").read_text())
    manifest["task"]["presentation"] = "pair"
    manifest["task"]["question"] = question
    (root / "manifest.json").write_text(json.dumps(manifest))


def test_preference_sign_convention(tmp_path):
    rows = pair_rows([{"winner": 1}, {"winner": -1}, {"winner": 0}])
    write_dataset(tmp_path, "preference", None, rows, image_ids=["a", "b"])
    patch_manifest(tmp_path, "preference")
    ds = load(tmp_path, split="train")
    winners = [ds[n][1] for n in range(3)]
    assert winners == [1, -1, 0]
    (obj_a, obj_b), _ = ds[0]
    assert obj_a is not None and obj_b is not None


def test_preference_dataloader_batches(tmp_path):
    rows = pair_rows([{"winner": 1}, {"winner": -1}])
    write_dataset(tmp_path, "preference", None, rows, image_ids=["a", "b"])
    patch_manifest(tmp_path, "preference")
    ds = load(tmp_path, split="train", transform=TO_TENSOR)
    (batch_a, batch_b), batch_w = next(iter(DataLoader(ds, batch_size=2)))
    assert batch_a.shape == (2, 8, 8, 3)
    assert batch_w.tolist() == [1, -1]


def test_similarity_continuous(tmp_path):
    rows = pair_rows([{"score": 0.8}])
    write_dataset(tmp_path, "similarity", None, rows, image_ids=["a", "b"])
    patch_manifest(tmp_path, "similarity")
    ds = load(tmp_path, split="train")
    (_, _), score = ds[0]
    assert score == 0.8


def test_similarity_binary_maps_to_float(tmp_path):
    rows = pair_rows([{"same": True}, {"same": False}])
    write_dataset(tmp_path, "similarity", None, rows, image_ids=["a", "b"])
    patch_manifest(tmp_path, "similarity")
    ds = load(tmp_path, split="train")
    assert ds[0][1] == 1.0
    assert ds[1][1] == 0.0
```

- [ ] **Step 2: テストを実行して失敗を確認**

Run: `uv run pytest tests/datasets/test_pair.py -v`
Expected: FAIL（`unsupported question type: 'preference'`）

- [ ] **Step 3: 実装**

`src/annotorch/datasets/pair.py`:

```python
from __future__ import annotations

from .base import AnnotorchDataset


class _PairDataset(AnnotorchDataset):
    def _load_pair(self, row):
        id_a, id_b = row["item_ids"]
        return self._load_obj(id_a), self._load_obj(id_b)


class PreferenceDataset(_PairDataset):
    def __getitem__(self, index: int):
        row = self.rows[index]
        # winner: 1 = item_ids の1番目の勝ち, -1 = 2番目, 0 = tie（skip は除外済み）
        return self._load_pair(row), row["answer"]["winner"]


class SimilarityDataset(_PairDataset):
    def __getitem__(self, index: int):
        row = self.rows[index]
        answer = row["answer"]
        score = float(answer["same"]) if "same" in answer else float(answer["score"])
        return self._load_pair(row), score
```

`src/annotorch/datasets/__init__.py` の `load()` の分岐を更新:

```python
    if question == "hard_label":
        from .classification import HardLabelDataset as cls
    elif question == "soft_label":
        from .classification import SoftLabelDataset as cls
    elif question == "preference":
        from .pair import PreferenceDataset as cls
    elif question == "similarity":
        from .pair import SimilarityDataset as cls
    else:
        raise ValueError(f"unsupported question type: {question}")
```

- [ ] **Step 4: テストを実行してパスを確認**

Run: `uv run pytest tests/datasets/test_pair.py -v`
Expected: 4 PASSED

- [ ] **Step 5: コミット**

```bash
git add src/annotorch/datasets/ tests/datasets/test_pair.py
git commit -m "feat: preference/similarity pair datasets"
```

---

### Task 12: グループ系 Dataset（datasets/group.py）

**Files:**
- Create: `src/annotorch/datasets/group.py`
- Modify: `src/annotorch/datasets/__init__.py`（load の分岐追加）
- Test: `tests/datasets/test_group.py`

**Interfaces:**
- Consumes: `AnnotorchDataset`（Task 10）
- Produces:
  - `RankingDataset` — `ds[i] -> (objs: list, ranks: torch.LongTensor(n,))`。`ranks[j]` = 提示順 j 番目のアイテムの順位（`answer["order"]` の何番目か。0が最良）
  - `GroupingDataset` — `ds[i] -> (objs: list, group_ids: torch.LongTensor(n,))`。`group_ids[j]` = 提示順 j 番目のアイテムが属するグループ番号
  - 両クラスとも `ds.collate_fn(batch) -> (list_of_obj_lists, list_of_tensors)`（可変長のためリストのまま返す）

- [ ] **Step 1: 失敗するテストを書く**

`tests/datasets/test_group.py`:

```python
import torch
from torch.utils.data import DataLoader

from annotorch.datasets import load

from .test_classification import write_dataset


def patch_manifest(root, question):
    import json
    manifest = json.loads((root / "manifest.json").read_text())
    manifest["task"]["presentation"] = "group"
    manifest["task"]["question"] = question
    (root / "manifest.json").write_text(json.dumps(manifest))


def test_ranking_dataset(tmp_path):
    rows = [{
        "unit_id": "u0",
        "item_ids": ["a", "b", "c"],
        "answer": {"order": ["c", "a", "b"]},  # c が最良
        "annotator_id": "default", "split": "train",
    }]
    write_dataset(tmp_path, "ranking", None, rows, image_ids=["a", "b", "c"])
    patch_manifest(tmp_path, "ranking")
    ds = load(tmp_path, split="train")
    objs, ranks = ds[0]
    assert len(objs) == 3
    # a は order[1] → rank 1, b は order[2] → rank 2, c は order[0] → rank 0
    assert ranks.tolist() == [1, 2, 0]
    assert ranks.dtype == torch.int64


def test_grouping_dataset(tmp_path):
    rows = [{
        "unit_id": "u0",
        "item_ids": ["a", "b", "c", "d"],
        "answer": {"groups": [["a", "d"], ["b", "c"]]},
        "annotator_id": "default", "split": "train",
    }]
    write_dataset(tmp_path, "grouping", None, rows, image_ids=["a", "b", "c", "d"])
    patch_manifest(tmp_path, "grouping")
    ds = load(tmp_path, split="train")
    objs, group_ids = ds[0]
    assert len(objs) == 4
    assert group_ids.tolist() == [0, 1, 1, 0]


def test_group_collate_fn_with_variable_sizes(tmp_path):
    rows = [
        {"unit_id": "u0", "item_ids": ["a", "b", "c"],
         "answer": {"order": ["a", "b", "c"]},
         "annotator_id": "default", "split": "train"},
        {"unit_id": "u1", "item_ids": ["a", "b"],
         "answer": {"order": ["b", "a"]},
         "annotator_id": "default", "split": "train"},
    ]
    write_dataset(tmp_path, "ranking", None, rows, image_ids=["a", "b", "c"])
    patch_manifest(tmp_path, "ranking")
    ds = load(tmp_path, split="train")
    loader = DataLoader(ds, batch_size=2, collate_fn=ds.collate_fn)
    obj_lists, rank_list = next(iter(loader))
    assert len(obj_lists) == 2
    assert len(obj_lists[0]) == 3 and len(obj_lists[1]) == 2
    assert rank_list[1].tolist() == [1, 0]
```

- [ ] **Step 2: テストを実行して失敗を確認**

Run: `uv run pytest tests/datasets/test_group.py -v`
Expected: FAIL（`unsupported question type: 'ranking'`）

- [ ] **Step 3: 実装**

`src/annotorch/datasets/group.py`:

```python
from __future__ import annotations

import torch

from .base import AnnotorchDataset


class _GroupDataset(AnnotorchDataset):
    @staticmethod
    def collate_fn(batch):
        """可変長グループ用: バッチ次元はリストのまま返す。"""
        objs = [b[0] for b in batch]
        targets = [b[1] for b in batch]
        return objs, targets

    def _load_objs(self, row):
        return [self._load_obj(item_id) for item_id in row["item_ids"]]


class RankingDataset(_GroupDataset):
    def __getitem__(self, index: int):
        row = self.rows[index]
        order = row["answer"]["order"]
        ranks = torch.tensor(
            [order.index(item_id) for item_id in row["item_ids"]], dtype=torch.int64
        )
        return self._load_objs(row), ranks


class GroupingDataset(_GroupDataset):
    def __getitem__(self, index: int):
        row = self.rows[index]
        group_of = {
            item_id: g
            for g, group in enumerate(row["answer"]["groups"])
            for item_id in group
        }
        group_ids = torch.tensor(
            [group_of[item_id] for item_id in row["item_ids"]], dtype=torch.int64
        )
        return self._load_objs(row), group_ids
```

`src/annotorch/datasets/__init__.py` の `load()` の分岐を更新（`else` の前に追加）:

```python
    elif question == "ranking":
        from .group import RankingDataset as cls
    elif question == "grouping":
        from .group import GroupingDataset as cls
```

- [ ] **Step 4: テストを実行してパスを確認**

Run: `uv run pytest tests/datasets/test_group.py -v`
Expected: 3 PASSED

- [ ] **Step 5: コミット**

```bash
git add src/annotorch/datasets/ tests/datasets/test_group.py
git commit -m "feat: ranking/grouping group datasets with collate_fn"
```

---

### Task 13: ラウンドトリップ統合テスト（services 経由）

**Files:**
- Test: `tests/test_roundtrip.py`

**Interfaces:**
- Consumes: services（ProjectService / TaskService / ExportService）と `datasets.load` — **ユースケース層だけを使い**、storage / domain を直接触らない
- Produces: 全質問タイプのエンドツーエンド検証（新規実装なし。失敗したら該当タスクの実装を修正する。テスト側の期待値は仕様なので変えない）

- [ ] **Step 1: 統合テストを書く**

`tests/test_roundtrip.py`:

```python
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
```

注意: `answer_fn` が受け取るのは `UnitDetail`（`items` は `Item` オブジェクトのリスト）。id が必要な回答では `[i.id for i in u.items]` で取り出す。

- [ ] **Step 2: テストを実行**

Run: `uv run pytest tests/test_roundtrip.py -v`
Expected: 9 PASSED

- [ ] **Step 3: 全体テストを実行**

Run: `uv run pytest tests/ -v`
Expected: 全タスクの全テストが PASSED

- [ ] **Step 4: コミット**

```bash
git add tests/test_roundtrip.py
git commit -m "test: end-to-end roundtrip tests through the services layer"
```

---

## 計画1の完了条件

- `uv run pytest tests/ -v` が全て PASSED
- レイヤー依存規則が守られている（`grep -rn "sqlite3" src/annotorch/ | grep -v storage/` がヒットしない、`grep -rn "from ..services\|from annotorch.services" src/annotorch/domain src/annotorch/storage src/annotorch/datasets` がヒットしない）
- スペックのうち以下は**計画2（FastAPIサーバー + CLI + Docker）/ 計画3（最小限のReact UI）に持ち越し**:
  - HTTP API・`annotorch serve` / `annotorch export` CLI・Dockerfile / docker-compose.yml
  - 全アノテーションUI・インポートUI・エクスポートUI（作り込みは最小限、全方式が操作できること優先）
  - フロントエンドの Vitest テスト
