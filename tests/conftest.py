"""Фикстуры: приложение с тестовой БД, клиент, пользователи, двойник модели."""

import shutil
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import Depends
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import testlab.models  # noqa: F401 — регистрирует модели в Base.metadata
from testlab.__main__ import create_app
from testlab.database import Base, create_engine, get_db
from testlab.dependencies.material import get_file_storage, get_llm_client
from testlab.dependencies.uow import get_uow
from testlab.infrastructure.storage import LocalFileStorage
from testlab.repositories.uow import UnitOfWork
from tests.helpers import FakeLLM, register

TEST_TMP_ROOT = Path(__file__).resolve().parents[1] / ".test-tmp"


@pytest.fixture
def tmp_path(request) -> Iterator[Path]:
    """Собственный tmp_path: системный temp в песочнице закрыт на запись."""
    safe_name = "".join(char if char.isalnum() else "-" for char in request.node.name)[:40]
    path = TEST_TMP_ROOT / f"{safe_name}-{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    yield path
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
async def engine(tmp_path: Path):
    database = tmp_path / "test.db"
    engine = create_engine(f"sqlite+aiosqlite:///{database.as_posix()}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
def session_maker(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture
async def session(session_maker) -> AsyncIterator[AsyncSession]:
    async with session_maker() as session:
        yield session


@pytest.fixture
def fake_llm() -> FakeLLM:
    return FakeLLM()


@pytest.fixture
def uploads_dir(tmp_path: Path) -> Path:
    return tmp_path / "uploads"


@pytest.fixture
def storage(uploads_dir: Path) -> LocalFileStorage:
    return LocalFileStorage(uploads_dir)


@pytest.fixture
def app(session_maker, fake_llm, storage):
    application = create_app()

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with session_maker() as session:
            yield session

    def override_get_uow(db: AsyncSession = Depends(override_get_db)) -> UnitOfWork:
        return UnitOfWork(db)

    application.dependency_overrides[get_db] = override_get_db
    application.dependency_overrides[get_uow] = override_get_uow
    application.dependency_overrides[get_file_storage] = lambda: storage
    application.dependency_overrides[get_llm_client] = lambda: fake_llm
    return application


@pytest.fixture
async def client(app) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def teacher(client) -> dict:
    return await register(client, "teacher_one", role="teacher")


@pytest.fixture
async def other_teacher(client) -> dict:
    return await register(client, "teacher_two", role="teacher")


@pytest.fixture
async def student(client) -> dict:
    return await register(client, "student_one", role="student")
