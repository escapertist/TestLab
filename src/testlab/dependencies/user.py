"""Провайдер сервиса пользователей."""

from fastapi import Depends

from testlab.dependencies.uow import get_uow
from testlab.repositories.uow import UnitOfWork
from testlab.services.user import UserService


def get_user_service(uow: UnitOfWork = Depends(get_uow)) -> UserService:
    return UserService(uow)
