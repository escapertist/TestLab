"""Единица работы: репозитории одной транзакции на use case."""

from sqlalchemy.ext.asyncio import AsyncSession

from testlab.repositories.material import MaterialRepository
from testlab.repositories.test import TestRepository
from testlab.repositories.user import UserRepository


class UnitOfWork:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.materials = MaterialRepository(session)
        self.tests = TestRepository(session)

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
