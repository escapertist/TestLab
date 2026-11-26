"""Хранилище загруженных файлов."""

import asyncio
import logging
import uuid
from pathlib import Path
from typing import Protocol

from testlab.errors import NotFoundError, PersistenceError

logger = logging.getLogger(__name__)

ALLOWED_SUFFIXES = frozenset({".pdf"})
MISSING_FILE_MESSAGE = "Файл материала не найден"


class FileStorage(Protocol):
    async def save(self, content: bytes, filename: str) -> str: ...

    async def read(self, path: str) -> bytes: ...

    async def delete(self, path: str) -> None: ...


class LocalFileStorage:
    """Файлы лежат в одном каталоге под уникальными именами."""

    def __init__(self, directory: str | Path) -> None:
        self._directory = Path(directory)

    async def save(self, content: bytes, filename: str) -> str:
        path = self._directory / f"{uuid.uuid4().hex}{self._suffix(filename)}"
        try:
            await asyncio.to_thread(self._directory.mkdir, parents=True, exist_ok=True)
            await asyncio.to_thread(path.write_bytes, content)
        except OSError as error:
            raise PersistenceError(f"Не удалось сохранить файл: {error}") from error
        return str(path)

    async def read(self, path: str) -> bytes:
        try:
            return await asyncio.to_thread(Path(path).read_bytes)
        except FileNotFoundError as error:
            raise NotFoundError(MISSING_FILE_MESSAGE) from error
        except OSError as error:
            raise PersistenceError(f"Не удалось прочитать файл: {error}") from error

    async def delete(self, path: str) -> None:
        # Удаление файла не должно ломать уже зафиксированное удаление записи.
        try:
            await asyncio.to_thread(Path(path).unlink, missing_ok=True)
        except OSError:
            logger.exception("Не удалось удалить файл материала: %s", path)

    @staticmethod
    def _suffix(filename: str) -> str:
        suffix = Path(filename).suffix.lower()
        return suffix if suffix in ALLOWED_SUFFIXES else ".pdf"
