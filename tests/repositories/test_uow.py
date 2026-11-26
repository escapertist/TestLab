"""Единица работы: коммит, откат, отсутствие коммитов в репозиториях."""

from pathlib import Path

from sqlalchemy import select

import testlab.repositories
from testlab.models.user import User
from testlab.repositories.uow import UnitOfWork


async def test_commit_persists(session_maker):
    async with session_maker() as session:
        uow = UnitOfWork(session)
        await uow.users.create(User(username="persisted", password_hash="x", full_name="Имя"))
        await uow.commit()

    async with session_maker() as session:
        found = await session.scalar(select(User).where(User.username == "persisted"))
    assert found is not None


async def test_rollback_discards(session_maker):
    async with session_maker() as session:
        uow = UnitOfWork(session)
        await uow.users.create(User(username="discarded", password_hash="x", full_name="Имя"))
        await uow.rollback()

    async with session_maker() as session:
        found = await session.scalar(select(User).where(User.username == "discarded"))
    assert found is None


def test_repositories_do_not_commit():
    directory = Path(testlab.repositories.__file__).parent
    for name in ("user.py", "material.py", "test.py"):
        text = (directory / name).read_text(encoding="utf-8")
        assert "session.commit" not in text, f"{name} коммитит сам"
