"""Извлечение текста из PDF."""

import pytest

from testlab.errors import MaterialValidationError
from testlab.infrastructure.pdf import extract_text
from tests.helpers import build_blank_pdf, build_pdf_with_text


def test_extracts_text():
    assert "Hello PDF" in extract_text(build_pdf_with_text("Hello PDF"))


def test_rejects_blank_pdf():
    with pytest.raises(MaterialValidationError, match="текстового слоя"):
        extract_text(build_blank_pdf())


def test_rejects_garbage():
    with pytest.raises(MaterialValidationError, match="Не удалось прочитать PDF"):
        extract_text(b"not a pdf at all")
