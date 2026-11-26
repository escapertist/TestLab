"""Сервисы пользователей и аутентификации."""

import pytest

from testlab.errors import InvalidCredentialsError, UserAlreadyExistsError
from testlab.models.enums import UserRole
from testlab.repositories.uow import UnitOfWork
from testlab.services.auth import AuthService
from testlab.services.user import UserService


async def test_register_creates_user(session_maker):
    async with session_maker() as session:
        user = await UserService(UnitOfWork(session)).register("alice", "password123", "Алиса", UserRole.teacher)

    assert user.username == "alice"
    assert user.role is UserRole.teacher
    assert user.password_hash != "password123"


async def test_duplicate_username(session_maker):
    async with session_maker() as session:
        service = UserService(UnitOfWork(session))
        await service.register("alice", "password123", "Алиса", UserRole.student)

        with pytest.raises(UserAlreadyExistsError):
            await service.register("alice", "password123", "Другая Алиса", UserRole.student)


async def test_login(session_maker):
    async with session_maker() as session:
        service = UserService(UnitOfWork(session))
        await service.register("alice", "password123", "Алиса", UserRole.student)

        user = await service.login("alice", "password123")

    assert user.username == "alice"


async def test_login_with_wrong_password(session_maker):
    async with session_maker() as session:
        service = UserService(UnitOfWork(session))
        await service.register("alice", "password123", "Алиса", UserRole.student)

        with pytest.raises(InvalidCredentialsError):
            await service.login("alice", "wrong-password")
        with pytest.raises(InvalidCredentialsError):
            await service.login("unknown", "password123")


async def test_issued_token_authenticates(session_maker):
    async with session_maker() as session:
        service = UserService(UnitOfWork(session))
        user = await service.register("alice", "password123", "Алиса", UserRole.teacher)
        token = service.issue_token(user)

    async with session_maker() as session:
        authenticated = await AuthService(UnitOfWork(session)).authenticate(token)

    assert authenticated.id == user.id


async def test_authenticate_rejects_bad_tokens(session_maker):
    async with session_maker() as session:
        service = AuthService(UnitOfWork(session))

        with pytest.raises(Exception, match="Не передан токен"):
            await service.authenticate(None)
        with pytest.raises(Exception, match="Неверный токен"):
            await service.authenticate("не-uuid")
        with pytest.raises(Exception, match="Пользователь не найден"):
            await service.authenticate("0a5a0b6a-1111-4222-8333-444455556666")
