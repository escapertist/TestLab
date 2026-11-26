"""Провайдер единицы работы."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from testlab.database import get_db
from testlab.repositories.uow import UnitOfWork


def get_uow(db: AsyncSession = Depends(get_db)) -> UnitOfWork:
    return UnitOfWork(db)
