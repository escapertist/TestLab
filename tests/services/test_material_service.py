"""Use case загрузки материала: атомарность, компенсация файла, владение."""

import inspect
from pathlib import Path

import pytest
from sqlalchemy import func, select

from testlab.config.app_config import settings
from testlab.errors import MaterialValidationError, NotFoundError, PersistenceError, UploadTooLargeError
from testlab.models.material import Material
from testlab.models.user import User
from testlab.repositories.uow import UnitOfWork
from testlab.services.material import MaterialService

TEXT = "текст материала"
CONTENT = b"%PDF-1.4 test"


@pytest.fixture(autouse=True)
def stub_pdf(monkeypatch) -> None:
    monkeypatch.setattr("testlab.services.material.extract_text", lambda content: TEXT)


async def create_user(uow: UnitOfWork, username: str = "teacher") -> User:
    user = await uow.users.create(User(username=username, password_hash="x", full_name="Преподаватель"))
    await uow.commit()
    return user


async def count_materials(session) -> int:
    return int(await session.scalar(select(func.count()).select_from(Material)) or 0)


async def test_uploads_material(session_maker, storage):
    async with session_maker() as session:
        uow = UnitOfWork(session)
        teacher = await create_user(uow)
        service = MaterialService(uow, storage)

        material = await service.upload_pdf(
            teacher_id=teacher.id,
            title="Лекция 1",
            filename="lecture.pdf",
            content_type="application/pdf",
            content=CONTENT,
        )

        assert material.teacher_id == teacher.id
        assert material.title == "Лекция 1"
        assert material.is_uploaded is True
        assert Path(material.file_path).read_bytes() == CONTENT


def test_service_does_not_accept_llm():
    assert list(inspect.signature(MaterialService).parameters) == ["uow", "storage"]


async def test_commit_failure_removes_file(session_maker, storage, uploads_dir, monkeypatch):
    async with session_maker() as session:
        uow = UnitOfWork(session)
        teacher = await create_user(uow)
        service = MaterialService(uow, storage)

        async def fail_commit(self) -> None:
            raise RuntimeError("нет соединения с БД")

        monkeypatch.setattr(UnitOfWork, "commit", fail_commit)

        with pytest.raises(PersistenceError):
            await service.upload_pdf(teacher.id, "Лекция", "lecture.pdf", "application/pdf", CONTENT)

    assert not uploads_dir.exists() or list(uploads_dir.iterdir()) == []
    async with session_maker() as session:
        assert await count_materials(session) == 0


async def test_upload_without_text_layer_saves_nothing(session_maker, storage, uploads_dir, monkeypatch):
    def fail(_: bytes) -> str:
        raise MaterialValidationError("В PDF нет текстового слоя (возможно, это скан)")

    monkeypatch.setattr("testlab.services.material.extract_text", fail)

    async with session_maker() as session:
        uow = UnitOfWork(session)
        teacher = await create_user(uow)
        service = MaterialService(uow, storage)

        with pytest.raises(MaterialValidationError):
            await service.upload_pdf(teacher.id, "Лекция", "lecture.pdf", "application/pdf", CONTENT)

        assert await count_materials(session) == 0
    assert not uploads_dir.exists() or list(uploads_dir.iterdir()) == []


async def test_validation_rejects_non_pdf(session_maker, storage):
    async with session_maker() as session:
        uow = UnitOfWork(session)
        teacher = await create_user(uow)
        service = MaterialService(uow, storage)

        with pytest.raises(MaterialValidationError, match="Нужен PDF"):
            await service.upload_pdf(teacher.id, "Лекция", "notes.txt", "application/pdf", CONTENT)


async def test_validation_rejects_too_large(session_maker, storage, monkeypatch):
    monkeypatch.setattr(settings, "uploads_max_bytes", 10)

    async with session_maker() as session:
        uow = UnitOfWork(session)
        teacher = await create_user(uow)
        service = MaterialService(uow, storage)

        with pytest.raises(UploadTooLargeError):
            await service.upload_pdf(teacher.id, "Лекция", "lecture.pdf", "application/pdf", CONTENT)


async def test_foreign_material_is_not_found(session_maker, storage):
    async with session_maker() as session:
        uow = UnitOfWork(session)
        owner = await create_user(uow, "owner")
        stranger = await create_user(uow, "stranger")
        service = MaterialService(uow, storage)
        material = await service.upload_pdf(owner.id, "Лекция", "lecture.pdf", "application/pdf", CONTENT)

        with pytest.raises(NotFoundError):
            await service.get_material(stranger.id, material.id)
        with pytest.raises(NotFoundError):
            await service.get_material_file(stranger.id, material.id)
        with pytest.raises(NotFoundError):
            await service.delete_material(stranger.id, material.id)


async def test_delete_removes_file_and_record(session_maker, storage):
    async with session_maker() as session:
        uow = UnitOfWork(session)
        teacher = await create_user(uow)
        service = MaterialService(uow, storage)
        material = await service.upload_pdf(teacher.id, "Лекция", "lecture.pdf", "application/pdf", CONTENT)
        path = Path(material.file_path)

        await service.delete_material(teacher.id, material.id)

        assert not path.exists()
        items, total = await service.list_materials(teacher.id, limit=10, offset=0)
        assert (items, total) == ([], 0)


async def test_delete_tolerates_missing_file(session_maker, storage):
    async with session_maker() as session:
        uow = UnitOfWork(session)
        teacher = await create_user(uow)
        service = MaterialService(uow, storage)
        material = await service.upload_pdf(teacher.id, "Лекция", "lecture.pdf", "application/pdf", CONTENT)
        Path(material.file_path).unlink()

        await service.delete_material(teacher.id, material.id)

        assert await count_materials(session) == 0


async def test_missing_file_is_not_found(session_maker, storage):
    async with session_maker() as session:
        uow = UnitOfWork(session)
        teacher = await create_user(uow)
        service = MaterialService(uow, storage)
        material = await service.upload_pdf(teacher.id, "Лекция", "lecture.pdf", "application/pdf", CONTENT)
        Path(material.file_path).unlink()

        with pytest.raises(NotFoundError, match="Файл материала"):
            await service.get_material_file(teacher.id, material.id)
