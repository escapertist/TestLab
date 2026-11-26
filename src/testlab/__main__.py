"""Сборка приложения и запуск сервера."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

import testlab.models  # noqa: F401 — регистрирует модели в Base.metadata
from testlab.database import async_engine, init_db
from testlab.errors import register_exception_handlers
from testlab.routers.answers import router as answers_router
from testlab.routers.material import router as material_router
from testlab.routers.test import router as test_router
from testlab.routers.user import router as user_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await init_db(async_engine)
    yield
    await async_engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="TestLab API", lifespan=lifespan)
    register_exception_handlers(app)
    app.include_router(user_router)
    app.include_router(material_router)
    app.include_router(test_router)
    app.include_router(answers_router)
    return app


app = create_app()


def main() -> None:
    uvicorn.run("testlab.__main__:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
