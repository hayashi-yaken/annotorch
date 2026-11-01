from __future__ import annotations

from pathlib import Path

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


def import_root(request: Request) -> Path:
    return request.app.state.import_root


def export_root(request: Request) -> Path:
    return request.app.state.export_root
