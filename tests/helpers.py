"""Вспомогательные функции и тестовые двойники."""

import json
from collections.abc import Iterator
from io import BytesIO

import httpx
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from testlab.llm.generation import GeneratedTest, parse_generated_test

PASSWORD = "secret123"


def build_pdf_with_text(text: str = "Hello PDF") -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
    )
    content = DecodedStreamObject()
    content.set_data(f"BT /F1 24 Tf 72 720 Td ({text}) Tj ET".encode("latin-1"))
    page[NameObject("/Contents")] = writer._add_object(content)

    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def build_blank_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def build_llm_response(title: str = "Тест по материалу", closed: int = 5, open_: int = 2) -> str:
    questions: list[dict] = []
    for index in range(closed):
        questions.append(
            {
                "type": "closed",
                "text": f"Закрытый вопрос {index + 1}",
                "points": 1,
                "options": [
                    {"text": "Верный вариант", "is_correct": True},
                    {"text": "Неверный вариант", "is_correct": False},
                ],
                "rubric": None,
            }
        )
    for index in range(open_):
        questions.append(
            {
                "type": "open",
                "text": f"Открытый вопрос {index + 1}",
                "points": 3,
                "options": None,
                "rubric": {"criteria_text": "Критерии", "reference_answer": "Эталон"},
            }
        )
    return json.dumps({"title": title, "questions": questions}, ensure_ascii=False)


class FakeLLM:
    """Подменяет GigaChatClient в сервисах и в DI."""

    def __init__(self, raw: str | None = None, error: Exception | None = None) -> None:
        self.raw = raw if raw is not None else build_llm_response()
        self.error = error
        self.calls: list[str] = []

    async def generate_test(self, text: str, closed_count: int = 5, open_count: int = 2) -> GeneratedTest:
        self.calls.append(text)
        if self.error is not None:
            raise self.error
        return parse_generated_test(self.raw)


async def register(client: httpx.AsyncClient, username: str, role: str = "teacher") -> dict:
    await client.post(
        "/auth/register",
        json={
            "username": username,
            "password": PASSWORD,
            "full_name": f"Пользователь {username}",
            "role": role,
        },
    )
    response = await client.post("/auth/login", json={"username": username, "password": PASSWORD})
    body = response.json()
    return {
        "id": body["id"],
        "token": body["access_token"],
        "headers": {"Authorization": f"Bearer {body['access_token']}"},
    }


async def upload_material(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    content: bytes | None = None,
    filename: str = "lecture.pdf",
    title: str = "Лекция 1",
    content_type: str = "application/pdf",
) -> httpx.Response:
    return await client.post(
        "/materials",
        files={"file": (filename, content if content is not None else build_pdf_with_text(), content_type)},
        data={"title": title},
        headers=headers,
    )


def iter_routes(app) -> Iterator:
    """Разворачивает вложенные роутеры FastAPI в плоский список."""
    stack = list(app.routes)
    while stack:
        route = stack.pop(0)
        nested = getattr(route, "original_router", None)
        if nested is not None:
            stack = list(nested.routes) + stack
        else:
            yield route


async def create_test(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    material_id: str,
    title: str | None = None,
) -> httpx.Response:
    kwargs = {"json": {"title": title}} if title is not None else {}
    return await client.post(f"/materials/{material_id}/tests", headers=headers, **kwargs)
