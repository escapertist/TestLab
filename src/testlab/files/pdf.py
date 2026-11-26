"""Извлечение текста из PDF."""

from io import BytesIO

from pypdf import PdfReader

from testlab.errors import MaterialValidationError


def extract_text(content: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(content))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as error:  # pypdf бросает разные типы на битых файлах
        raise MaterialValidationError(f"Не удалось прочитать PDF: {error}") from error

    text = text.strip()
    if not text:
        raise MaterialValidationError("В PDF нет текстового слоя (возможно, это скан)")
    return text
