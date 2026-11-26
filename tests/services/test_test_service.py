"""Use case создания теста по материалу: владение, конфликт, атомарность."""

from pathlib import Path

import pytest
from sqlalchemy import func, select

from testlab.config.app_config import settings
from testlab.errors import ConflictError, LLMError, NotFoundError, PersistenceError
from testlab.models.material import Material
from testlab.models.test import Test
from testlab.models.user import User
from testlab.repositories.uow import UnitOfWork
from testlab.services.material import MaterialService
from testlab.services.test import TestService
from tests.helpers import FakeLLM

TEXT = "текст материала"
CONTENT = b"%PDF-1.4 test"


@pytest.fixture(autouse=True)
def stub_pdf(monkeypatch) -> None:
    monkeypatch.setattr("testlab.services.material.extract_text", lambda content: TEXT)
    monkeypatch.setattr("testlab.services.test.extract_text", lambda content: TEXT)


async def create_user(uow: UnitOfWork, username: str = "teacher") -> User:
    user = await uow.users.create(User(username=username, password_hash="x", full_name="Преподаватель"))
    await uow.commit()
    return user


async def upload_material(uow: UnitOfWork, storage, teacher_id: str) -> Material:
    service = MaterialService(uow, storage)
    return await service.upload_pdf(teacher_id, "Лекция", "lecture.pdf", "application/pdf", CONTENT)


async def count_tests(session) -> int:
    return int(await session.scalar(select(func.count()).select_from(Test)) or 0)


async def generate(service: TestService, teacher_id: str, material_id: str, title: str | None = None) -> Test:
    return await service.generate_for_material(
        teacher_id,
        material_id,
        title,
        closed_count=5,
        open_count=2,
        options_count=4,
    )


async def test_creates_test_with_questions(session_maker, storage, fake_llm):
    async with session_maker() as session:
        uow = UnitOfWork(session)
        teacher = await create_user(uow)
        material = await upload_material(uow, storage, teacher.id)
        service = TestService(uow, storage, fake_llm)

        test = await generate(service, teacher.id, material.id)

        assert test.material_id == material.id
        assert test.teacher_id == teacher.id
        assert test.title == "Тест по материалу"
        assert test.generation_params["model"] == settings.llm.generation_model
        assert test.generation_params["closed_count"] == 5
        assert test.generation_params["open_count"] == 2
        assert test.generation_params["options_count"] == 4
        assert test.generation_params["text_chars"] == len(TEXT)
        assert test.generation_params["text_truncated"] is False
        assert len(test.questions) == 7
        assert len(test.questions[0].options) == 4
        assert test.questions[-1].reference_answer == "Эталон"
        assert fake_llm.calls == [TEXT]


async def test_title_from_request_wins(session_maker, storage, fake_llm):
    async with session_maker() as session:
        uow = UnitOfWork(session)
        teacher = await create_user(uow)
        material = await upload_material(uow, storage, teacher.id)
        service = TestService(uow, storage, fake_llm)

        test = await generate(service, teacher.id, material.id, title="Итоговый тест")

    assert test.title == "Итоговый тест"


async def test_counts_are_passed_to_model(session_maker, storage, fake_llm):
    async with session_maker() as session:
        uow = UnitOfWork(session)
        teacher = await create_user(uow)
        material = await upload_material(uow, storage, teacher.id)
        service = TestService(uow, storage, fake_llm)

        await service.generate_for_material(
            teacher.id,
            material.id,
            closed_count=3,
            open_count=1,
            options_count=3,
        )

    assert fake_llm.counts == [(3, 1, 3)]


async def test_second_generation_conflicts(session_maker, storage, fake_llm):
    async with session_maker() as session:
        uow = UnitOfWork(session)
        teacher = await create_user(uow)
        material = await upload_material(uow, storage, teacher.id)
        service = TestService(uow, storage, fake_llm)
        first = await generate(service, teacher.id, material.id)

        with pytest.raises(ConflictError, match="уже создан"):
            await generate(service, teacher.id, material.id)

        assert await count_tests(session) == 1
        assert fake_llm.calls == [TEXT]
    assert first.id


async def test_foreign_material_is_not_found(session_maker, storage, fake_llm):
    async with session_maker() as session:
        uow = UnitOfWork(session)
        owner = await create_user(uow, "owner")
        stranger = await create_user(uow, "stranger")
        material = await upload_material(uow, storage, owner.id)
        service = TestService(uow, storage, fake_llm)

        with pytest.raises(NotFoundError, match="Материал не найден"):
            await generate(service, stranger.id, material.id)


async def test_missing_file_is_not_found(session_maker, storage, fake_llm):
    async with session_maker() as session:
        uow = UnitOfWork(session)
        teacher = await create_user(uow)
        material = await upload_material(uow, storage, teacher.id)
        Path(material.file_path).unlink()
        service = TestService(uow, storage, fake_llm)

        with pytest.raises(NotFoundError, match="Файл материала не найден"):
            await generate(service, teacher.id, material.id)


async def test_llm_error_leaves_no_test(session_maker, storage):
    llm = FakeLLM(error=LLMError("GigaChat недоступен"))

    async with session_maker() as session:
        uow = UnitOfWork(session)
        teacher = await create_user(uow)
        material = await upload_material(uow, storage, teacher.id)
        service = TestService(uow, storage, llm)

        with pytest.raises(LLMError):
            await generate(service, teacher.id, material.id)

        assert await count_tests(session) == 0


async def test_commit_failure_leaves_no_test(session_maker, storage, fake_llm, monkeypatch):
    async with session_maker() as session:
        uow = UnitOfWork(session)
        teacher = await create_user(uow)
        material = await upload_material(uow, storage, teacher.id)
        service = TestService(uow, storage, fake_llm)

        async def fail_commit(self) -> None:
            raise RuntimeError("нет соединения с БД")

        monkeypatch.setattr(UnitOfWork, "commit", fail_commit)

        with pytest.raises(PersistenceError, match="Не удалось сохранить тест"):
            await generate(service, teacher.id, material.id)

    async with session_maker() as session:
        assert await count_tests(session) == 0
        assert await session.scalar(select(func.count()).select_from(Material)) == 1


async def test_generation_params_report_actual_text_length(session_maker, storage, monkeypatch):
    monkeypatch.setattr("testlab.services.test.extract_text", lambda content: "а" * 50)
    monkeypatch.setattr(settings.llm, "max_input_chars", 10)

    async with session_maker() as session:
        uow = UnitOfWork(session)
        teacher = await create_user(uow)
        material = await upload_material(uow, storage, teacher.id)
        service = TestService(uow, storage, FakeLLM())

        test = await generate(service, teacher.id, material.id)

    assert test.generation_params["text_chars"] == 10
    assert test.generation_params["text_truncated"] is True
