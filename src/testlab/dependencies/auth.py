"""Провайдеры аутентификации: сборка зависимостей без бизнес-логики."""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from testlab.dependencies.uow import get_uow
from testlab.models.user import User
from testlab.repositories.uow import UnitOfWork
from testlab.services.auth import AuthService

bearer_scheme = HTTPBearer(auto_error=False)


def get_auth_service(uow: UnitOfWork = Depends(get_uow)) -> AuthService:
    return AuthService(uow)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    service: AuthService = Depends(get_auth_service),
) -> User:
    token = credentials.credentials if credentials is not None else None
    return await service.authenticate(token)


async def get_current_teacher(
    user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> User:
    return service.require_teacher(user)


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentTeacher = Annotated[User, Depends(get_current_teacher)]
