"""Провайдер сервиса тестов."""

from fastapi import Depends

from testlab.dependencies.material import get_file_storage, get_llm_client
from testlab.dependencies.uow import get_uow
from testlab.infrastructure.storage import FileStorage
from testlab.llm.client import GigaChatClient
from testlab.repositories.uow import UnitOfWork
from testlab.services.test import TestService


def get_test_service(
    uow: UnitOfWork = Depends(get_uow),
    storage: FileStorage = Depends(get_file_storage),
    llm: GigaChatClient = Depends(get_llm_client),
) -> TestService:
    return TestService(uow, storage, llm)
