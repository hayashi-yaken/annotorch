from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .. import __version__
from ..services.exports import ExportService
from ..services.projects import ProjectService
from ..services.tasks import TaskService
from ..storage.workspace import Workspace
from .errors import install_error_handlers
from .routers import annotations, export, items, projects, tasks

STATIC_DIR = Path(__file__).parent / "static"


def create_app(root: Path | str) -> FastAPI:
    app = FastAPI(title="annotorch")
    ws = Workspace(root)
    app.state.projects = ProjectService(ws)
    app.state.tasks = TaskService(ws)
    app.state.exports = ExportService(ws)

    install_error_handlers(app)

    # 計画3の開発サーバー（vite, :5173）からのアクセス用
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health():
        return {"status": "ok", "version": __version__}

    app.include_router(projects.router, prefix="/api")
    app.include_router(items.router, prefix="/api")
    app.include_router(tasks.router, prefix="/api")
    app.include_router(annotations.router, prefix="/api")
    app.include_router(export.router, prefix="/api")

    if STATIC_DIR.is_dir():
        app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

    return app
