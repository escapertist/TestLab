"""Репозиторий пользователей."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from testlab.errors import UserAlreadyExistsError
from testlab.models.user import User

DUPLICATE_USERNAME_MESSAGE = "Пользователь с таким username уже существует"


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_username(self, username: str) -> User | None:
        result = await self.session.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: str) -> User | None:
        return await self.session.get(User, user_id)

    async def create(self, user: User) -> User:
        self.session.add(user)
        try:
            await self.session.flush()
        except IntegrityError as error:
            # Уникальный индекс срабатывает раньше проверки в сервисе.
            raise UserAlreadyExistsError(DUPLICATE_USERNAME_MESSAGE) from error
        return user
