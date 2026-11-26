"""Регистрация и вход пользователя."""

from testlab.errors import InvalidCredentialsError, UserAlreadyExistsError
from testlab.models.enums import UserRole
from testlab.models.user import User
from testlab.repositories.uow import UnitOfWork
from testlab.repositories.user import DUPLICATE_USERNAME_MESSAGE
from testlab.security import get_password_hash, verify_password


class UserService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def register(self, username: str, password: str, full_name: str, role: UserRole) -> User:
        if await self.uow.users.get_by_username(username) is not None:
            raise UserAlreadyExistsError(DUPLICATE_USERNAME_MESSAGE)

        user = User(
            username=username,
            password_hash=get_password_hash(password),
            full_name=full_name,
            role=role,
        )
        await self.uow.users.create(user)
        await self.uow.commit()
        return user

    async def login(self, username: str, password: str) -> User:
        user = await self.uow.users.get_by_username(username)
        if user is None or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError("Неверный логин или пароль")
        return user

    @staticmethod
    def issue_token(user: User) -> str:
        """Заглушка вместо JWT: токен — это id пользователя."""
        return str(user.id)
