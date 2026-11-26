"""Аутентификация и проверка роли."""

from uuid import UUID

from testlab.errors import InvalidTokenError, PermissionDeniedError
from testlab.models.enums import UserRole
from testlab.models.user import User
from testlab.repositories.uow import UnitOfWork


class AuthService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def authenticate(self, token: str | None) -> User:
        if not token:
            raise InvalidTokenError("Не передан токен")

        try:
            user_id = str(UUID(token))
        except ValueError as error:
            raise InvalidTokenError("Неверный токен") from error

        user = await self.uow.users.get_by_id(user_id)
        if user is None:
            raise InvalidTokenError("Пользователь не найден")
        return user

    def require_teacher(self, user: User) -> User:
        if user.role != UserRole.teacher:
            raise PermissionDeniedError("Действие доступно только преподавателю")
        return user
