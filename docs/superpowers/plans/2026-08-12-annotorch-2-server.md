# annotorch 計画2: FastAPI サーバー + CLI + Docker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 計画1の services 層を REST API として公開する FastAPI サーバー、services を呼ぶ CLI、Docker 起動環境を完成させる。計画3のReactフロントエンドはこのAPIだけを叩く。

**Architecture:** `server/` はHTTPアダプタに徹する。`create_app(root)` が Workspace と3つのサービス（ProjectService / TaskService / ExportService）を生成して `app.state` に置き、リソース単位の router（projects / items / tasks / annotations / export）が `Depends` でサービスを受け取って呼ぶだけ。例外→HTTPステータスの変換はアプリ全体のハンドラで一元化。`cli.py` も同じ services を呼ぶ対等なアダプタ。ビルド済みフロントは `server/static/` から配信し、デプロイは Docker（`docker compose up`）が主経路。

**Tech Stack:** FastAPI, uvicorn, python-multipart（いずれも `[server]` extra）、httpx（テスト用 dev 依存）、Docker / docker compose。

**前提:** 計画1（`2026-08-12-annotorch-1-core.md`）が完了していること。
**参照スペック:** `docs/superpowers/specs/2026-08-12-annotorch-design.md`

## Global Constraints

- 計画1の Global Constraints をすべて引き継ぐ（uv、レイヤー依存規則、preference winner = `1/-1/0/null` など）
- FastAPI / uvicorn / python-multipart は `[server]` extra のみ。server 以外のレイヤーから import しない
- **router にロジックを書かない**: routerは「HTTP入出力の変換 + サービス呼び出し」のみ。SQLite・ファイル形式・検証ルールを知るのは下のレイヤー
- 例外マッピングはアプリ全体のハンドラで一元化: `LookupError` → 404、`ValueError`（`AnswerValidationError` 含む）→ 400、`FileExistsError` → 409
- エンドポイントはすべて `/api` プレフィックス配下。静的配信は `/`
- サーバーのポートは 8000（compose で `8000:8000`）
- テスト環境の同期は `uv sync --extra server`、実行は `uv run pytest tests/ -v`

---

### Task 1: サーバー scaffolding（create_app + health + 例外ハンドラ + DI）

**Files:**
- Modify: `pyproject.toml`（dev 依存に httpx 追加）
- Create: `src/annotorch/server/__init__.py`（空）
- Create: `src/annotorch/server/app.py`
- Create: `src/annotorch/server/schemas.py`
- Create: `src/annotorch/server/routers/__init__.py`（空）
- Create: `src/annotorch/server/routers/deps.py`
- Create: `tests/server/__init__.py`（空）
- Create: `tests/server/conftest.py`
- Test: `tests/server/test_health.py`

**Interfaces:**
- Consumes: `Workspace`、`ProjectService` / `TaskService` / `ExportService`（計画1）
- Produces:
  - `create_app(root: Path | str) -> FastAPI` — サービスを `app.state.projects / .tasks / .exports` に載せる。以降のタスクは router を足して `include_router` を1行追加する
  - `GET /api/health` → `{"status": "ok", "version": "0.1.0"}`
  - 例外→HTTPステータスの一元ハンドラ（Global Constraints 参照）
  - `routers/deps.py`: `project_service(request) -> ProjectService` / `task_service(request) -> TaskService` / `export_service(request) -> ExportService`（`app.state` から取り出す Depends 用関数）
  - `schemas.py`: `ProjectCreate`, `FolderImport`, `TaskCreate`, `AnnotationIn`, `ExportIn`
  - テスト用 `client` fixture と `make_png_bytes()` / `create_project()` / `upload_pngs()` ヘルパ

- [ ] **Step 1: dev 依存を追加して同期**

`pyproject.toml` の dependency-groups を変更:

```toml
[dependency-groups]
dev = ["pytest>=8.0", "httpx>=0.27"]
```

```bash
uv sync --extra server
```

- [ ] **Step 2: 失敗するテストを書く**

`tests/server/conftest.py`:

```python
import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from annotorch.server.app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(tmp_path / "root")
    with TestClient(app) as c:
        yield c


def make_png_bytes(color=(255, 0, 0)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), color).save(buf, format="PNG")
    return buf.getvalue()


def create_project(client, name="p") -> str:
    return client.post("/api/projects", json={"name": name}).json()["id"]


def upload_pngs(client, pid: str, n: int) -> None:
    files = [
        ("files", (f"{k}.png", make_png_bytes((k * 60 % 256, 0, 0)), "image/png"))
        for k in range(n)
    ]
    res = client.post(f"/api/projects/{pid}/items/upload", files=files)
    assert res.status_code == 200 and res.json()["imported"] == n
```

（`create_project` / `upload_pngs` は Task 2 / 3 のルート実装後に有効になる。ここでは定義だけ置く）

`tests/server/test_health.py`:

```python
def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["version"] == "0.1.0"
```

- [ ] **Step 3: テストを実行して失敗を確認**

Run: `uv run pytest tests/server/test_health.py -v`
Expected: FAIL（`ModuleNotFoundError: annotorch.server.app`）

- [ ] **Step 4: 実装**

`src/annotorch/server/schemas.py`:

```python
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ..domain.models import Presentation, QuestionType, TaskConfig


class ProjectCreate(BaseModel):
    name: str
    description: str = ""


class FolderImport(BaseModel):
    path: str


class TaskCreate(BaseModel):
    name: str
    presentation: Presentation
    question: QuestionType
    config: TaskConfig = Field(default_factory=TaskConfig)


class AnnotationIn(BaseModel):
    answer: dict[str, Any]


class ExportIn(BaseModel):
    output_dir: str
    splits: dict[str, float] | None = None
    seed: int = 0
```

`src/annotorch/server/routers/deps.py`:

```python
from __future__ import annotations

from fastapi import Request

from ...services.exports import ExportService
from ...services.projects import ProjectService
from ...services.tasks import TaskService


def project_service(request: Request) -> ProjectService:
    return request.app.state.projects


def task_service(request: Request) -> TaskService:
    return request.app.state.tasks


def export_service(request: Request) -> ExportService:
    return request.app.state.exports
```

`src/annotorch/server/app.py`:

```python
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .. import __version__
from ..services.exports import ExportService
from ..services.projects import ProjectService
from ..services.tasks import TaskService
from ..storage.workspace import Workspace

STATIC_DIR = Path(__file__).parent / "static"


def create_app(root: Path | str) -> FastAPI:
    app = FastAPI(title="annotorch")
    ws = Workspace(root)
    app.state.projects = ProjectService(ws)
    app.state.tasks = TaskService(ws)
    app.state.exports = ExportService(ws)

    # 計画3の開発サーバー（vite, :5173）からのアクセス用
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(LookupError)
    async def _not_found(request: Request, exc: LookupError):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ValueError)  # AnswerValidationError も ValueError
    async def _bad_request(request: Request, exc: ValueError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(FileExistsError)
    async def _conflict(request: Request, exc: FileExistsError):
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.get("/api/health")
    def health():
        return {"status": "ok", "version": __version__}

    # Task 2〜6 でここに router を追加していく:
    # app.include_router(projects.router, prefix="/api")

    if STATIC_DIR.is_dir():
        app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

    return app
```

- [ ] **Step 5: テストを実行してパスを確認**

Run: `uv run pytest tests/server/test_health.py -v`
Expected: PASS

- [ ] **Step 6: コミット**

```bash
git add pyproject.toml src/annotorch/server/ tests/server/
git commit -m "feat: FastAPI app skeleton (DI, error handlers, health)"
```

---

### Task 2: projects router

**Files:**
- Create: `src/annotorch/server/routers/projects.py`
- Modify: `src/annotorch/server/app.py`（include_router 追加）
- Test: `tests/server/test_projects.py`

**Interfaces:**
- Consumes: `ProjectService`（create / list / delete）
- Produces:
  - `GET /api/projects` → `list[Project]`
  - `POST /api/projects` body `{name, description?}` → 201, `Project`
  - `DELETE /api/projects/{pid}` → `{"ok": true}`（未知は 404 — ハンドラ経由）

- [ ] **Step 1: 失敗するテストを書く**

`tests/server/test_projects.py`:

```python
def test_create_and_list_projects(client):
    res = client.post("/api/projects", json={"name": "demo", "description": "d"})
    assert res.status_code == 201
    body = res.json()
    assert body["name"] == "demo"
    listed = client.get("/api/projects").json()
    assert [p["id"] for p in listed] == [body["id"]]


def test_delete_project(client):
    pid = client.post("/api/projects", json={"name": "x"}).json()["id"]
    assert client.delete(f"/api/projects/{pid}").json() == {"ok": True}
    assert client.get("/api/projects").json() == []


def test_delete_unknown_project_404(client):
    assert client.delete("/api/projects/nope").status_code == 404
```

- [ ] **Step 2: テストを実行して失敗を確認**

Run: `uv run pytest tests/server/test_projects.py -v`
Expected: FAIL（404 Not Found）

- [ ] **Step 3: 実装**

`src/annotorch/server/routers/projects.py`:

```python
from __future__ import annotations

from fastapi import APIRouter, Depends

from ...services.projects import ProjectService
from ..schemas import ProjectCreate
from .deps import project_service

router = APIRouter()


@router.get("/projects")
def list_projects(svc: ProjectService = Depends(project_service)):
    return svc.list()


@router.post("/projects", status_code=201)
def create_project(body: ProjectCreate,
                   svc: ProjectService = Depends(project_service)):
    return svc.create(body.name, body.description)


@router.delete("/projects/{pid}")
def delete_project(pid: str, svc: ProjectService = Depends(project_service)):
    svc.delete(pid)
    return {"ok": True}
```

`src/annotorch/server/app.py` — import と登録を追加:

```python
from .routers import projects
```

health エンドポイント定義の後、static mount の前に:

```python
    app.include_router(projects.router, prefix="/api")
```

- [ ] **Step 4: テストを実行してパスを確認**

Run: `uv run pytest tests/server/test_projects.py -v`
Expected: 3 PASSED

- [ ] **Step 5: コミット**

```bash
git add src/annotorch/server/ tests/server/test_projects.py
git commit -m "feat: projects router"
```

---

### Task 3: items router（アップロード / フォルダ取り込み / 一覧 / 画像配信）

**Files:**
- Create: `src/annotorch/server/routers/items.py`
- Modify: `src/annotorch/server/app.py`（include_router 追加）
- Test: `tests/server/test_items.py`

**Interfaces:**
- Consumes: `ProjectService`（list_items / item_file_path / import_images / import_texts_jsonl / import_texts_csv）
- Produces:
  - `GET /api/projects/{pid}/items` → `list[Item]`
  - `POST /api/projects/{pid}/items/upload` — multipart `files`（画像複数）→ `ImportReport`。非画像はスキップ報告
  - `POST /api/projects/{pid}/items/upload-texts` — multipart `file`（.jsonl / .csv 1つ）→ `ImportReport`。他拡張子は 400
  - `POST /api/projects/{pid}/items/import-folder` body `{path}` → `ImportReport`。ディレクトリでなければ 400
  - `GET /api/projects/{pid}/items/{item_id}/file` → 画像の `FileResponse`。テキストItemや未知IDは 404

- [ ] **Step 1: 失敗するテストを書く**

`tests/server/test_items.py`:

```python
import json

from .conftest import create_project, make_png_bytes


def test_upload_images_and_list(client):
    pid = create_project(client)
    res = client.post(f"/api/projects/{pid}/items/upload", files=[
        ("files", ("a.png", make_png_bytes(), "image/png")),
        ("files", ("b.png", make_png_bytes((0, 255, 0)), "image/png")),
        ("files", ("c.txt", b"hello", "text/plain")),
    ])
    assert res.status_code == 200
    report = res.json()
    assert report["imported"] == 2
    assert len(report["skipped"]) == 1

    items = client.get(f"/api/projects/{pid}/items").json()
    assert len(items) == 2
    assert all(i["modality"] == "image" for i in items)


def test_item_file_served(client):
    pid = create_project(client)
    client.post(f"/api/projects/{pid}/items/upload",
                files=[("files", ("a.png", make_png_bytes(), "image/png"))])
    item = client.get(f"/api/projects/{pid}/items").json()[0]
    res = client.get(f"/api/projects/{pid}/items/{item['id']}/file")
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/png"


def test_item_file_unknown_404(client):
    pid = create_project(client)
    assert client.get(f"/api/projects/{pid}/items/nope/file").status_code == 404


def test_upload_texts_jsonl(client):
    pid = create_project(client)
    lines = "\n".join([json.dumps({"text": "hello"}), json.dumps({"text": "world"})])
    res = client.post(f"/api/projects/{pid}/items/upload-texts",
                      files={"file": ("t.jsonl", lines.encode(), "application/jsonl")})
    assert res.status_code == 200
    assert res.json()["imported"] == 2
    items = client.get(f"/api/projects/{pid}/items").json()
    assert items[0]["text"] == "hello"


def test_upload_texts_wrong_extension_400(client):
    pid = create_project(client)
    res = client.post(f"/api/projects/{pid}/items/upload-texts",
                      files={"file": ("t.txt", b"x", "text/plain")})
    assert res.status_code == 400


def test_import_folder(client, tmp_path):
    from PIL import Image

    pid = create_project(client)
    src = tmp_path / "folder"
    src.mkdir()
    Image.new("RGB", (8, 8)).save(src / "x.png")
    res = client.post(f"/api/projects/{pid}/items/import-folder",
                      json={"path": str(src)})
    assert res.status_code == 200
    assert res.json()["imported"] == 1


def test_import_folder_bad_path_400(client):
    pid = create_project(client)
    res = client.post(f"/api/projects/{pid}/items/import-folder",
                      json={"path": "/no/such/dir"})
    assert res.status_code == 400
```

- [ ] **Step 2: テストを実行して失敗を確認**

Run: `uv run pytest tests/server/test_items.py -v`
Expected: FAIL

- [ ] **Step 3: 実装**

`src/annotorch/server/routers/items.py`:

```python
from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ...services.projects import ProjectService
from ..schemas import FolderImport
from .deps import project_service

router = APIRouter()


@router.get("/projects/{pid}/items")
def list_items(pid: str, svc: ProjectService = Depends(project_service)):
    return svc.list_items(pid)


@router.post("/projects/{pid}/items/upload")
async def upload_images(pid: str, files: list[UploadFile],
                        svc: ProjectService = Depends(project_service)):
    with tempfile.TemporaryDirectory() as tmp:
        for f in files:
            name = Path(f.filename or "unnamed").name
            (Path(tmp) / name).write_bytes(await f.read())
        return svc.import_images(pid, Path(tmp))


@router.post("/projects/{pid}/items/upload-texts")
async def upload_texts(pid: str, file: UploadFile,
                       svc: ProjectService = Depends(project_service)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".jsonl", ".csv"}:
        raise HTTPException(400, f"expected .jsonl or .csv (got {suffix!r})")
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / f"upload{suffix}"
        p.write_bytes(await file.read())
        if suffix == ".jsonl":
            return svc.import_texts_jsonl(pid, p)
        return svc.import_texts_csv(pid, p)


@router.post("/projects/{pid}/items/import-folder")
def import_folder(pid: str, body: FolderImport,
                  svc: ProjectService = Depends(project_service)):
    src = Path(body.path)
    if not src.is_dir():
        raise HTTPException(400, f"not a directory: {body.path}")
    return svc.import_images(pid, src)


@router.get("/projects/{pid}/items/{item_id}/file")
def item_file(pid: str, item_id: str,
              svc: ProjectService = Depends(project_service)):
    return FileResponse(svc.item_file_path(pid, item_id))
```

`src/annotorch/server/app.py` — import を `from .routers import items, projects` に変更し、登録を追加:

```python
    app.include_router(items.router, prefix="/api")
```

- [ ] **Step 4: テストを実行してパスを確認**

Run: `uv run pytest tests/server/test_items.py -v`
Expected: 7 PASSED

- [ ] **Step 5: コミット**

```bash
git add src/annotorch/server/ tests/server/test_items.py
git commit -m "feat: items router (import, list, file serving)"
```

---

### Task 4: tasks router（作成 = Unit生成込み、進捗付き一覧）

**Files:**
- Create: `src/annotorch/server/routers/tasks.py`
- Modify: `src/annotorch/server/app.py`（include_router 追加）
- Test: `tests/server/test_tasks.py`

**Interfaces:**
- Consumes: `TaskService`（create_task / list_tasks_with_progress）
- Produces:
  - `POST /api/projects/{pid}/tasks` body = `schemas.TaskCreate` → 201, `{"task": Task, "num_units": int}`。不正な組み合わせ・生成不能は 400（services の ValueError → ハンドラ）
  - `GET /api/projects/{pid}/tasks` → `list[TaskWithProgress]`

- [ ] **Step 1: 失敗するテストを書く**

`tests/server/test_tasks.py`:

```python
from .conftest import create_project, upload_pngs


def test_create_task_generates_units(client):
    pid = create_project(client)
    upload_pngs(client, pid, 4)
    res = client.post(f"/api/projects/{pid}/tasks", json={
        "name": "cls", "presentation": "single", "question": "hard_label",
        "config": {"labels": ["cat", "dog"]},
    })
    assert res.status_code == 201
    body = res.json()
    assert body["num_units"] == 4
    assert body["task"]["question"] == "hard_label"


def test_create_task_invalid_combination_400(client):
    pid = create_project(client)
    upload_pngs(client, pid, 4)
    res = client.post(f"/api/projects/{pid}/tasks", json={
        "name": "bad", "presentation": "single", "question": "preference",
        "config": {},
    })
    assert res.status_code == 400


def test_create_pair_task_without_num_units_400(client):
    pid = create_project(client)
    upload_pngs(client, pid, 4)
    res = client.post(f"/api/projects/{pid}/tasks", json={
        "name": "pref", "presentation": "pair", "question": "preference",
        "config": {},
    })
    assert res.status_code == 400


def test_list_tasks_with_progress(client):
    pid = create_project(client)
    upload_pngs(client, pid, 3)
    client.post(f"/api/projects/{pid}/tasks", json={
        "name": "cls", "presentation": "single", "question": "hard_label",
        "config": {"labels": ["a", "b"]},
    })
    tasks = client.get(f"/api/projects/{pid}/tasks").json()
    assert len(tasks) == 1
    assert tasks[0]["total_units"] == 3
    assert tasks[0]["answered_units"] == 0
```

- [ ] **Step 2: テストを実行して失敗を確認**

Run: `uv run pytest tests/server/test_tasks.py -v`
Expected: FAIL

- [ ] **Step 3: 実装**

`src/annotorch/server/routers/tasks.py`:

```python
from __future__ import annotations

from fastapi import APIRouter, Depends

from ...services.tasks import TaskService
from ..schemas import TaskCreate
from .deps import task_service

router = APIRouter()


@router.post("/projects/{pid}/tasks", status_code=201)
def create_task(pid: str, body: TaskCreate,
                svc: TaskService = Depends(task_service)):
    task, num_units = svc.create_task(pid, body.name, body.presentation,
                                      body.question, body.config)
    return {"task": task, "num_units": num_units}


@router.get("/projects/{pid}/tasks")
def list_tasks(pid: str, svc: TaskService = Depends(task_service)):
    return svc.list_tasks_with_progress(pid)
```

`src/annotorch/server/app.py` — import を `from .routers import items, projects, tasks` に変更し、登録を追加:

```python
    app.include_router(tasks.router, prefix="/api")
```

- [ ] **Step 4: テストを実行してパスを確認**

Run: `uv run pytest tests/server/test_tasks.py -v`
Expected: 4 PASSED

- [ ] **Step 5: コミット**

```bash
git add src/annotorch/server/ tests/server/test_tasks.py
git commit -m "feat: tasks router"
```

---

### Task 5: annotations router（Unit取得 + 回答保存）

**Files:**
- Create: `src/annotorch/server/routers/annotations.py`
- Modify: `src/annotorch/server/app.py`（include_router 追加）
- Test: `tests/server/test_annotations.py`

**Interfaces:**
- Consumes: `TaskService`（list_units / save_answer）
- Produces:
  - `GET /api/projects/{pid}/tasks/{tid}/units` → `list[UnitDetail]`（position順、既存回答入り）
  - `PUT /api/projects/{pid}/tasks/{tid}/units/{uid}/annotation` body `{"answer": {...}}` → `{"unit_id", "answer"}`。不正回答は 400、未知Unitは 404（services の例外 → ハンドラ）

- [ ] **Step 1: 失敗するテストを書く**

`tests/server/test_annotations.py`:

```python
from .conftest import create_project, upload_pngs


def setup_task(client, pid):
    return client.post(f"/api/projects/{pid}/tasks", json={
        "name": "cls", "presentation": "single", "question": "hard_label",
        "config": {"labels": ["cat", "dog"]},
    }).json()["task"]


def test_list_units_expands_items(client):
    pid = create_project(client)
    upload_pngs(client, pid, 3)
    task = setup_task(client, pid)
    units = client.get(f"/api/projects/{pid}/tasks/{task['id']}/units").json()
    assert len(units) == 3
    assert [u["position"] for u in units] == [0, 1, 2]
    assert units[0]["answer"] is None
    assert units[0]["items"][0]["modality"] == "image"


def test_save_annotation_updates_progress(client):
    pid = create_project(client)
    upload_pngs(client, pid, 2)
    task = setup_task(client, pid)
    units = client.get(f"/api/projects/{pid}/tasks/{task['id']}/units").json()

    res = client.put(
        f"/api/projects/{pid}/tasks/{task['id']}/units/{units[0]['id']}/annotation",
        json={"answer": {"label": "cat"}})
    assert res.status_code == 200
    assert res.json()["answer"] == {"label": "cat"}

    units = client.get(f"/api/projects/{pid}/tasks/{task['id']}/units").json()
    assert units[0]["answer"] == {"label": "cat"}
    tasks = client.get(f"/api/projects/{pid}/tasks").json()
    assert tasks[0]["answered_units"] == 1


def test_save_invalid_annotation_400(client):
    pid = create_project(client)
    upload_pngs(client, pid, 1)
    task = setup_task(client, pid)
    units = client.get(f"/api/projects/{pid}/tasks/{task['id']}/units").json()
    res = client.put(
        f"/api/projects/{pid}/tasks/{task['id']}/units/{units[0]['id']}/annotation",
        json={"answer": {"label": "bird"}})
    assert res.status_code == 400


def test_save_annotation_unknown_unit_404(client):
    pid = create_project(client)
    upload_pngs(client, pid, 1)
    task = setup_task(client, pid)
    res = client.put(
        f"/api/projects/{pid}/tasks/{task['id']}/units/nope/annotation",
        json={"answer": {"label": "cat"}})
    assert res.status_code == 404
```

- [ ] **Step 2: テストを実行して失敗を確認**

Run: `uv run pytest tests/server/test_annotations.py -v`
Expected: FAIL

- [ ] **Step 3: 実装**

`src/annotorch/server/routers/annotations.py`:

```python
from __future__ import annotations

from fastapi import APIRouter, Depends

from ...services.tasks import TaskService
from ..schemas import AnnotationIn
from .deps import task_service

router = APIRouter()


@router.get("/projects/{pid}/tasks/{tid}/units")
def list_units(pid: str, tid: str, svc: TaskService = Depends(task_service)):
    return svc.list_units(pid, tid)


@router.put("/projects/{pid}/tasks/{tid}/units/{uid}/annotation")
def save_annotation(pid: str, tid: str, uid: str, body: AnnotationIn,
                    svc: TaskService = Depends(task_service)):
    answer = svc.save_answer(pid, tid, uid, body.answer)
    return {"unit_id": uid, "answer": answer}
```

`src/annotorch/server/app.py` — import を `from .routers import annotations, items, projects, tasks` に変更し、登録を追加:

```python
    app.include_router(annotations.router, prefix="/api")
```

- [ ] **Step 4: テストを実行してパスを確認**

Run: `uv run pytest tests/server/test_annotations.py -v`
Expected: 4 PASSED

- [ ] **Step 5: コミット**

```bash
git add src/annotorch/server/ tests/server/test_annotations.py
git commit -m "feat: annotations router (units listing, answer saving)"
```

---

### Task 6: export router

**Files:**
- Create: `src/annotorch/server/routers/export.py`
- Modify: `src/annotorch/server/app.py`（include_router 追加）
- Test: `tests/server/test_export_api.py`

**Interfaces:**
- Consumes: `ExportService.export`
- Produces: `POST /api/projects/{pid}/tasks/{tid}/export` body = `schemas.ExportIn` → `ExportResult`。出力先既存は 409、不正な splits は 400（いずれも services の例外 → ハンドラ）

- [ ] **Step 1: 失敗するテストを書く**

`tests/server/test_export_api.py`:

```python
from .conftest import create_project, upload_pngs


def make_task(client, pid):
    return client.post(f"/api/projects/{pid}/tasks", json={
        "name": "cls", "presentation": "single", "question": "hard_label",
        "config": {"labels": ["cat", "dog"]},
    }).json()["task"]


def annotate_all(client, pid, task_id, labels=("cat", "dog")):
    units = client.get(f"/api/projects/{pid}/tasks/{task_id}/units").json()
    for n, unit in enumerate(units):
        client.put(
            f"/api/projects/{pid}/tasks/{task_id}/units/{unit['id']}/annotation",
            json={"answer": {"label": labels[n % len(labels)]}})


def test_export(client, tmp_path):
    pid = create_project(client)
    upload_pngs(client, pid, 4)
    task = make_task(client, pid)
    annotate_all(client, pid, task["id"])

    out = tmp_path / "ds"
    res = client.post(f"/api/projects/{pid}/tasks/{task['id']}/export",
                      json={"output_dir": str(out)})
    assert res.status_code == 200
    assert res.json()["num_rows"] == 4
    assert (out / "manifest.json").exists()


def test_export_existing_dir_409(client, tmp_path):
    pid = create_project(client)
    upload_pngs(client, pid, 1)
    task = make_task(client, pid)
    annotate_all(client, pid, task["id"])
    out = tmp_path / "ds"
    out.mkdir()
    res = client.post(f"/api/projects/{pid}/tasks/{task['id']}/export",
                      json={"output_dir": str(out)})
    assert res.status_code == 409


def test_export_invalid_splits_400(client, tmp_path):
    pid = create_project(client)
    upload_pngs(client, pid, 1)
    task = make_task(client, pid)
    annotate_all(client, pid, task["id"])
    res = client.post(f"/api/projects/{pid}/tasks/{task['id']}/export",
                      json={"output_dir": str(tmp_path / "x"),
                            "splits": {"train": 0.5, "test": 0.2}})
    assert res.status_code == 400
```

- [ ] **Step 2: テストを実行して失敗を確認**

Run: `uv run pytest tests/server/test_export_api.py -v`
Expected: FAIL

- [ ] **Step 3: 実装**

`src/annotorch/server/routers/export.py`:

```python
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends

from ...services.exports import ExportService
from ..schemas import ExportIn
from .deps import export_service

router = APIRouter()


@router.post("/projects/{pid}/tasks/{tid}/export")
def export_task(pid: str, tid: str, body: ExportIn,
                svc: ExportService = Depends(export_service)):
    return svc.export(pid, tid, Path(body.output_dir),
                      splits=body.splits, seed=body.seed)
```

`src/annotorch/server/app.py` — import を `from .routers import annotations, export, items, projects, tasks` に変更し、登録を追加:

```python
    app.include_router(export.router, prefix="/api")
```

- [ ] **Step 4: テストを実行してパスを確認**

Run: `uv run pytest tests/server/test_export_api.py -v`
Expected: 3 PASSED

- [ ] **Step 5: コミット**

```bash
git add src/annotorch/server/ tests/server/test_export_api.py
git commit -m "feat: export router"
```

---

### Task 7: CLI（cli.py: ls / export / serve）+ 静的配信テスト

**Files:**
- Create: `src/annotorch/cli.py`
- Create: `tests/test_cli.py`
- Test: `tests/test_cli.py`, `tests/server/test_static.py`

**Interfaces:**
- Consumes: `ProjectService` / `TaskService` / `ExportService`（HTTPと同じ services）、`create_app`
- Produces: `main(argv: list[str] | None = None) -> int`（`[project.scripts]` が参照）
  - `annotorch ls [--root PATH]` — プロジェクトと各タスク（進捗付き）の一覧
  - `annotorch export --project PID --task TID --out DIR [--root PATH] [--splits "train=0.8,test=0.2"] [--seed N]`
  - `annotorch serve [--root PATH] [--host HOST] [--port PORT] [--no-browser]` — uvicorn 起動。`[server]` extra 未導入なら分かりやすいエラーで exit 1
  - `--root` のデフォルトは `~/.annotorch`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_cli.py`:

```python
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
```

`tests/server/test_static.py`:

```python
from fastapi.testclient import TestClient

from annotorch.server import app as app_module


def test_static_served_when_built(tmp_path, monkeypatch):
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("<html>annotorch-ui</html>")
    monkeypatch.setattr(app_module, "STATIC_DIR", static)
    client = TestClient(app_module.create_app(tmp_path / "root"))
    res = client.get("/")
    assert res.status_code == 200
    assert "annotorch-ui" in res.text


def test_api_still_works_with_static(tmp_path, monkeypatch):
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("<html></html>")
    monkeypatch.setattr(app_module, "STATIC_DIR", static)
    client = TestClient(app_module.create_app(tmp_path / "root"))
    assert client.get("/api/health").status_code == 200
```

- [ ] **Step 2: テストを実行して失敗を確認**

Run: `uv run pytest tests/test_cli.py tests/server/test_static.py -v`
Expected: CLI 4件が FAIL（`ModuleNotFoundError: annotorch.cli`）。static 2件は Task 1 実装済みのため PASS で良い

- [ ] **Step 3: 実装**

`src/annotorch/cli.py`:

```python
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .services.exports import ExportService
from .services.projects import ProjectService
from .services.tasks import TaskService
from .storage.workspace import Workspace

DEFAULT_ROOT = Path.home() / ".annotorch"


def _parse_splits(text: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for part in text.split(","):
        name, _, value = part.partition("=")
        out[name.strip()] = float(value)
    return out


def _cmd_ls(args: argparse.Namespace) -> int:
    ws = Workspace(args.root)
    tasks_svc = TaskService(ws)
    for project in ProjectService(ws).list():
        print(f"{project.id}  {project.name}")
        for t in tasks_svc.list_tasks_with_progress(project.id):
            print(f"  {t.id}  {t.name}"
                  f"  {t.presentation.value}/{t.question.value}"
                  f"  {t.answered_units}/{t.total_units}")
    return 0


def _cmd_export(args: argparse.Namespace) -> int:
    svc = ExportService(Workspace(args.root))
    result = svc.export(
        args.project, args.task, Path(args.out),
        splits=_parse_splits(args.splits) if args.splits else None,
        seed=args.seed,
    )
    print(f"exported {result.num_rows} annotations to {result.output_dir}")
    if result.num_unanswered_units:
        print(f"warning: {result.num_unanswered_units} unanswered units were excluded")
    if result.num_skipped:
        print(f"warning: {result.num_skipped} skipped answers were excluded")
    print("\nload it with:\n"
          "  from annotorch.datasets import load\n"
          f"  ds = load({str(result.output_dir)!r}, split=\"train\")")
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    try:
        import uvicorn

        from .server.app import create_app
    except ImportError:
        print(
            "error: server dependencies are not installed."
            " install with: pip install 'annotorch[server]'",
            file=sys.stderr,
        )
        return 1
    app = create_app(args.root)
    if not args.no_browser:
        import threading
        import webbrowser

        url = f"http://{args.host}:{args.port}"
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    uvicorn.run(app, host=args.host, port=args.port)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="annotorch")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ls = sub.add_parser("ls", help="list projects and tasks")
    p_ls.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    p_ls.set_defaults(func=_cmd_ls)

    p_export = sub.add_parser("export", help="export a task to a dataset directory")
    p_export.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    p_export.add_argument("--project", required=True)
    p_export.add_argument("--task", required=True)
    p_export.add_argument("--out", required=True)
    p_export.add_argument("--splits", default=None,
                          help='e.g. "train=0.8,test=0.2"')
    p_export.add_argument("--seed", type=int, default=0)
    p_export.set_defaults(func=_cmd_export)

    p_serve = sub.add_parser("serve", help="start the annotation server")
    p_serve.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8000)
    p_serve.add_argument("--no-browser", action="store_true")
    p_serve.set_defaults(func=_cmd_serve)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: テストを実行してパスを確認**

Run: `uv run pytest tests/test_cli.py tests/server/test_static.py -v`
Expected: 全て PASSED

手動確認:

```bash
uv run annotorch serve --root /tmp/annotorch-smoke --no-browser &
sleep 2 && curl -s http://127.0.0.1:8000/api/health
kill %1
```

Expected: `{"status":"ok","version":"0.1.0"}`

- [ ] **Step 5: コミット**

```bash
git add src/annotorch/cli.py tests/
git commit -m "feat: CLI adapter (ls, export, serve) over services"
```

---

### Task 8: Dockerfile + docker-compose.yml

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `.dockerignore`

**Interfaces:**
- Consumes: `[server]` extra、`annotorch serve`
- Produces: `docker compose up` で `http://localhost:8000` にサーバーが立つ。作業データは named volume `annotorch-data`（`/data`）に永続化。ホストの `./import` が `/import`（読み取り専用）にマウントされ、フォルダ取り込みに使える
- 注: この時点ではフロント未ビルドなので `/` は404、`/api/*` のみ動く。計画3 Task 7 で node ビルドステージを追加する

- [ ] **Step 1: ファイルを書く**

`.dockerignore`:

```
.git
.venv
.pytest_cache
__pycache__
*.egg-info
tests
docs
frontend/node_modules
```

`Dockerfile`:

```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir ".[server]"
EXPOSE 8000
CMD ["annotorch", "serve", "--root", "/data", "--host", "0.0.0.0", "--port", "8000", "--no-browser"]
```

（torch を含むためイメージは数GBになる。ローカル用途なので許容。気になる場合は CPU wheel のインデックス指定で縮められるが v1 ではやらない）

`docker-compose.yml`:

```yaml
services:
  annotorch:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - annotorch-data:/data
      - ./import:/import:ro

volumes:
  annotorch-data:
```

- [ ] **Step 2: ビルドと起動を手動確認**

```bash
cd /Users/hayashinaofumi/workspace/hayashi-yaken/annotorch
mkdir -p import
docker compose up --build -d
sleep 3
curl -s http://localhost:8000/api/health
curl -s -X POST http://localhost:8000/api/projects \
  -H 'Content-Type: application/json' -d '{"name": "smoke"}'
docker compose down
```

Expected: health が `{"status":"ok",...}`、projects が作成した project の JSON を返す

- [ ] **Step 3: コミット**

```bash
git add Dockerfile docker-compose.yml .dockerignore
git commit -m "feat: Docker image and compose setup for the annotation server"
```

---

### Task 9: API ラウンドトリップ統合テスト

**Files:**
- Test: `tests/server/test_api_roundtrip.py`

**Interfaces:**
- Consumes: 全APIエンドポイント + `annotorch.datasets.load`
- Produces: 「HTTP経由の操作だけで作ったデータセットが `datasets.load` で読める」ことの検証（新規実装なし。失敗したら該当タスクを修正）

- [ ] **Step 1: 統合テストを書く**

`tests/server/test_api_roundtrip.py`:

```python
import numpy as np
import torch
from torch.utils.data import DataLoader

from annotorch.datasets import load

from .conftest import create_project, upload_pngs

TO_TENSOR = lambda img: torch.from_numpy(np.array(img, dtype=np.float32) / 255.0)


def test_api_roundtrip_hard_label(client, tmp_path):
    pid = create_project(client, "rt")
    upload_pngs(client, pid, 4)
    task = client.post(f"/api/projects/{pid}/tasks", json={
        "name": "cls", "presentation": "single", "question": "hard_label",
        "config": {"labels": ["cat", "dog"]},
    }).json()["task"]

    units = client.get(f"/api/projects/{pid}/tasks/{task['id']}/units").json()
    for n, unit in enumerate(units):
        res = client.put(
            f"/api/projects/{pid}/tasks/{task['id']}/units/{unit['id']}/annotation",
            json={"answer": {"label": "cat" if n % 2 == 0 else "dog"}})
        assert res.status_code == 200

    out = tmp_path / "exported"
    res = client.post(f"/api/projects/{pid}/tasks/{task['id']}/export",
                      json={"output_dir": str(out)})
    assert res.status_code == 200
    assert res.json()["num_rows"] == 4

    ds = load(out, split="train", transform=TO_TENSOR)
    x, y = next(iter(DataLoader(ds, batch_size=4)))
    assert x.shape == (4, 8, 8, 3)
    assert sorted(y.tolist()) == [0, 0, 1, 1]


def test_api_roundtrip_preference_with_skip(client, tmp_path):
    pid = create_project(client, "rt-pref")
    upload_pngs(client, pid, 4)
    task = client.post(f"/api/projects/{pid}/tasks", json={
        "name": "pref", "presentation": "pair", "question": "preference",
        "config": {"num_units": 3, "seed": 0},
    }).json()["task"]

    units = client.get(f"/api/projects/{pid}/tasks/{task['id']}/units").json()
    answers = [{"winner": 1}, {"winner": None}, {"winner": -1}]
    for unit, answer in zip(units, answers):
        res = client.put(
            f"/api/projects/{pid}/tasks/{task['id']}/units/{unit['id']}/annotation",
            json={"answer": answer})
        assert res.status_code == 200

    out = tmp_path / "exported-pref"
    body = client.post(f"/api/projects/{pid}/tasks/{task['id']}/export",
                       json={"output_dir": str(out)}).json()
    assert body["num_rows"] == 2
    assert body["num_skipped"] == 1

    ds = load(out, split="train")
    assert [ds[n][1] for n in range(2)] == [1, -1]
```

- [ ] **Step 2: テストを実行**

Run: `uv run pytest tests/server/test_api_roundtrip.py -v`
Expected: 2 PASSED

- [ ] **Step 3: 全体テストを実行**

Run: `uv run pytest tests/ -v`
Expected: 計画1・2の全テストが PASSED

- [ ] **Step 4: コミット**

```bash
git add tests/server/test_api_roundtrip.py
git commit -m "test: API-level roundtrip tests"
```

---

## 計画2の完了条件

- `uv run pytest tests/ -v` 全パス
- `docker compose up` で `/api/health` が応答する
- router にビジネスロジックが無い（router 内で `SqliteStore` / `sqlite3` / `validate_answer` / `generate_units` を直接使っていない）
- スペックのうち**計画3に持ち越し**: 全画面のReact UI、フロントのビルド成果物の実運用（配信機構はTask 7で検証済み）、Dockerfile への node ビルドステージ追加
