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
