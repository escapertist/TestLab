"""Провайдер сервиса тестов."""

from fastapi import Depends

from testlab.dependencies.llm import get_generation_client
from testlab.dependencies.material import get_file_storage
from testlab.dependencies.uow import get_uow
from testlab.infrastructure.storage import FileStorage
from testlab.llm.client import TestGenerator
from testlab.repositories.uow import UnitOfWork
from testlab.services.test import TestService


def get_test_service(
    uow: UnitOfWork = Depends(get_uow),
    storage: FileStorage = Depends(get_file_storage),
    llm: TestGenerator = Depends(get_generation_client),
) -> TestService:
    return TestService(uow, storage, llm)
