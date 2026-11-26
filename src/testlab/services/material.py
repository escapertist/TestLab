"""Бизнес-логика учебных материалов."""

from pathlib import Path

from testlab.config.app_config import settings
from testlab.errors import (
    MaterialValidationError,
    NotFoundError,
    PersistenceError,
    UploadTooLargeError,
)
from testlab.infrastructure.pdf import extract_text
from testlab.infrastructure.storage import FileStorage
from testlab.models.material import Material
from testlab.models.test import Test
from testlab.repositories.uow import UnitOfWork

MEGABYTE = 1024 * 1024


class MaterialService:
    def __init__(self, uow: UnitOfWork, storage: FileStorage) -> None:
        self.uow = uow
        self.storage = storage

    async def upload_pdf(
        self,
        teacher_id: str,
        title: str,
        filename: str,
        content_type: str | None,
        content: bytes,
    ) -> Material:
        self._validate_upload(filename, content_type, content)
        # Извлекаем текст только как проверку: файл должен читаться и содержать текст.
        extract_text(content)

        file_path = await self.storage.save(content, filename)
        try:
            material = await self.uow.materials.create(
                Material(
                    teacher_id=teacher_id,
                    title=title,
                    file_path=file_path,
                    filename=filename,
                    is_uploaded=True,
                )
            )
            await self.uow.commit()
        except Exception as error:
            # Компенсация: транзакции нет, файл уже на диске.
            await self.uow.rollback()
            await self.storage.delete(file_path)
            raise PersistenceError("Не удалось сохранить материал") from error
        return material

    async def list_materials(self, teacher_id: str, limit: int, offset: int) -> tuple[list[Material], int]:
        return await self.uow.materials.list_by_teacher(teacher_id, limit, offset)

    async def get_material(self, teacher_id: str, material_id: str) -> tuple[Material, Test | None]:
        material = await self._require_material(teacher_id, material_id)
        test = await self.uow.tests.get_by_material(material.id)
        return material, test

    async def get_material_file(self, teacher_id: str, material_id: str) -> tuple[Material, Path]:
        material = await self._require_material(teacher_id, material_id)
        path = Path(material.file_path)
        if not path.is_file():
            raise NotFoundError("Файл материала не найден")
        return material, path

    async def delete_material(self, teacher_id: str, material_id: str) -> None:
        material = await self._require_material(teacher_id, material_id)
        file_path = material.file_path
        try:
            await self.uow.materials.delete(material)
            await self.uow.commit()
        except Exception as error:
            await self.uow.rollback()
            raise PersistenceError("Не удалось удалить материал") from error
        await self.storage.delete(file_path)

    async def _require_material(self, teacher_id: str, material_id: str) -> Material:
        material = await self.uow.materials.get_by_id_and_teacher(material_id, teacher_id)
        if material is None:
            raise NotFoundError("Материал не найден")
        return material

    @staticmethod
    def _validate_upload(filename: str, content_type: str | None, content: bytes) -> None:
        if not filename.lower().endswith(".pdf"):
            raise MaterialValidationError("Нужен PDF-файл")
        if content_type and content_type != "application/pdf":
            raise MaterialValidationError("Нужен PDF-файл")
        if not content:
            raise MaterialValidationError("Файл пустой")
        if len(content) > settings.uploads_max_bytes:
            megabytes = settings.uploads_max_bytes // MEGABYTE
            raise UploadTooLargeError(f"Файл больше {megabytes} МБ")
