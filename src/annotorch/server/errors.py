"""例外を HTTP レスポンスに変換し、サーバーログに残す。"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from ..errors import AnnotorchError, ConflictError, InvalidInputError, NotFoundError

logger = logging.getLogger("annotorch.server")

_CLIENT_ERRORS: tuple[tuple[type[AnnotorchError], int], ...] = (
    (NotFoundError, 404),
    (InvalidInputError, 400),
    (ConflictError, 409),
)


def status_for(exc: AnnotorchError) -> int:
    """例外に対応する HTTP ステータス。呼び出し側に原因がないものは 500。"""
    for cls, status in _CLIENT_ERRORS:
        if isinstance(exc, cls):
            return status
    return 500


def _describe(request: Request, status: int, kind: str, message: object) -> str:
    return f"{request.method} {request.url.path} -> {status} {kind}: {message}"


def _internal_error() -> JSONResponse:
    return JSONResponse(status_code=500,
                        content={"detail": "internal server error (see server log)"})


def install_error_handlers(app: FastAPI) -> None:
    """annotorch の例外を 4xx/5xx に変換し、すべての失敗をログに残すようにする。"""

    @app.exception_handler(AnnotorchError)
    async def _annotorch_error(request: Request, exc: AnnotorchError):
        status = status_for(exc)
        line = _describe(request, status, type(exc).__name__, exc)
        if status >= 500:
            logger.error(line, exc_info=exc)
            return _internal_error()
        logger.warning(line)
        return JSONResponse(status_code=status, content={"detail": str(exc)})

    @app.exception_handler(RequestValidationError)
    async def _request_validation(request: Request, exc: RequestValidationError):
        summary = "; ".join(
            f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()
        )
        logger.warning(_describe(request, 422, "RequestValidationError", summary))
        return await request_validation_exception_handler(request, exc)

    # exception_handler(Exception) だと Starlette が再送出して uvicorn も同じ
    # トレースバックを出すため、ミドルウェアで受け止めて1回だけ記録する。
    @app.middleware("http")
    async def _unexpected_error(request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:
            logger.error(_describe(request, 500, type(exc).__name__, exc), exc_info=exc)
            return _internal_error()
