"""Доменные исключения и их маппинг в HTTP-ответы."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError


class DomainError(Exception):
    """Базовая ошибка домена; роутеры её не перехватывают."""


class UserAlreadyExistsError(DomainError):
    pass


class InvalidCredentialsError(DomainError):
    pass


class InvalidTokenError(DomainError):
    pass


class PermissionDeniedError(DomainError):
    pass


class NotFoundError(DomainError):
    pass


class ConflictError(DomainError):
    pass


class MaterialValidationError(DomainError):
    pass


class UploadTooLargeError(DomainError):
    pass


class PersistenceError(DomainError):
    pass


class LLMError(DomainError):
    pass


class LLMResponseError(LLMError):
    """Ответ модели не соответствует контракту теста."""


_STATUS_BY_ERROR: dict[type[Exception], int] = {
    InvalidCredentialsError: 401,
    InvalidTokenError: 401,
    PermissionDeniedError: 403,
    NotFoundError: 404,
    ConflictError: 409,
    UserAlreadyExistsError: 400,
    MaterialValidationError: 400,
    UploadTooLargeError: 413,
    LLMError: 502,
    PersistenceError: 500,
}


def _make_handler(status_code: int):
    async def handler(_: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=status_code, content={"detail": str(exc)})

    return handler


async def _integrity_error_handler(_: Request, __: IntegrityError) -> JSONResponse:
    # Детали SQL не отдаём клиенту: ответ не должен раскрывать схему БД.
    return JSONResponse(status_code=400, content={"detail": "Данные уже существуют"})


def register_exception_handlers(app: FastAPI) -> None:
    for error_type, status_code in _STATUS_BY_ERROR.items():
        app.add_exception_handler(error_type, _make_handler(status_code))
    app.add_exception_handler(IntegrityError, _integrity_error_handler)
