"""Файловое хранилище."""

from pathlib import Path

import pytest

from testlab.errors import NotFoundError
from testlab.infrastructure.storage import LocalFileStorage


async def test_save_creates_file(tmp_path: Path):
    storage = LocalFileStorage(tmp_path / "uploads")

    path = await storage.save(b"%PDF-1.4", "lecture.pdf")

    assert Path(path).read_bytes() == b"%PDF-1.4"
    assert Path(path).suffix == ".pdf"
    assert Path(path).parent == tmp_path / "uploads"


async def test_save_normalizes_suffix(tmp_path: Path):
    storage = LocalFileStorage(tmp_path / "uploads")

    assert Path(await storage.save(b"data", "notes.txt")).suffix == ".pdf"
    assert Path(await storage.save(b"data", "LECTURE.PDF")).suffix == ".pdf"


async def test_read_returns_bytes(tmp_path: Path):
    storage = LocalFileStorage(tmp_path / "uploads")
    path = await storage.save(b"%PDF-1.4 content", "lecture.pdf")

    assert await storage.read(path) == b"%PDF-1.4 content"


async def test_read_missing_file(tmp_path: Path):
    storage = LocalFileStorage(tmp_path / "uploads")

    with pytest.raises(NotFoundError, match="Файл материала не найден"):
        await storage.read(str(tmp_path / "uploads" / "absent.pdf"))


async def test_delete_removes_file(tmp_path: Path):
    storage = LocalFileStorage(tmp_path / "uploads")
    path = await storage.save(b"data", "lecture.pdf")

    await storage.delete(path)

    assert not Path(path).exists()


async def test_delete_missing_file_is_silent(tmp_path: Path):
    storage = LocalFileStorage(tmp_path / "uploads")

    await storage.delete(str(tmp_path / "uploads" / "absent.pdf"))
