"""Провайдеры сервиса материалов и его инфраструктуры."""

from fastapi import Depends

from testlab.config.app_config import settings
from testlab.dependencies.uow import get_uow
from testlab.infrastructure.storage import FileStorage, LocalFileStorage
from testlab.llm.client import GigaChatClient
from testlab.repositories.uow import UnitOfWork
from testlab.services.material import MaterialService

_llm_client = GigaChatClient(settings.llm)


def get_llm_client() -> GigaChatClient:
    return _llm_client


def get_file_storage() -> FileStorage:
    return LocalFileStorage(settings.uploads_dir)


def get_material_service(
    uow: UnitOfWork = Depends(get_uow),
    storage: FileStorage = Depends(get_file_storage),
) -> MaterialService:
    return MaterialService(uow, storage)
