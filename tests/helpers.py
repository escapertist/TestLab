"""Вспомогательные функции и тестовые двойники."""

from collections.abc import Iterator
from io import BytesIO

import httpx
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from testlab.llm.output import Option, Question, Test
from testlab.models.enums import QuestionType

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


def build_generated_test(
    title: str = "Тест по материалу",
    closed: int = 5,
    open_: int = 2,
    options_count: int = 2,
) -> Test:
    questions: list[Question] = []
    for index in range(closed):
        options = [Option(text="Верный вариант", is_correct=True)]
        for option_index in range(1, options_count):
            options.append(Option(text=f"Неверный вариант {option_index}", is_correct=False))
        questions.append(Question(type=QuestionType.closed, text=f"Закрытый вопрос {index + 1}", options=options))
    for index in range(open_):
        questions.append(
            Question(
                type=QuestionType.open,
                text=f"Открытый вопрос {index + 1}",
                reference_answer="Эталон",
            )
        )
    return Test(title=title, questions=questions)


class FakeLLM:
    """Подменяет TestGenerator в сервисах и в DI."""

    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[str] = []
        self.counts: list[tuple[int, int, int]] = []

    async def generate_test(
        self,
        text: str,
        *,
        closed_count: int,
        open_count: int,
        options_count: int,
    ) -> Test:
        self.calls.append(text)
        self.counts.append((closed_count, open_count, options_count))
        if self.error is not None:
            raise self.error
        return build_generated_test(closed=closed_count, open_=open_count, options_count=options_count)


class FakeChecker:
    """Подменяет AnswerChecker в сервисах и в DI."""

    def __init__(self, verdict: bool = True, error: Exception | None = None) -> None:
        self.verdict = verdict
        self.error = error
        self.calls: list[tuple[str, str, str]] = []

    async def check_answer(self, question: str, correct_answer: str, user_answer: str) -> bool:
        self.calls.append((question, correct_answer, user_answer))
        if self.error is not None:
            raise self.error
        return self.verdict


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
    **fields,
) -> httpx.Response:
    body: dict = dict(fields)
    if title is not None:
        body["title"] = title
    kwargs = {"json": body} if body else {}
    return await client.post(f"/materials/{material_id}/tests", headers=headers, **kwargs)
