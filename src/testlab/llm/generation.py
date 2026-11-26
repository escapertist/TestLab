"""Типы сгенерированного теста и правила разбора ответа модели."""

import json
from dataclasses import dataclass

from testlab.errors import LLMResponseError
from testlab.models.enums import QuestionType

CLOSED_QUESTIONS_REQUIRED = 5
OPEN_QUESTIONS_REQUIRED = 2
MIN_POINTS = 1.0
MAX_POINTS = 5.0
DEFAULT_POINTS = 1.0
MIN_CLOSED_OPTIONS = 2
FENCE_LANGUAGES = frozenset({"json", "json5"})


@dataclass(frozen=True)
class GeneratedOption:
    text: str
    is_correct: bool


@dataclass(frozen=True)
class GeneratedRubric:
    criteria_text: str
    reference_answer: str


@dataclass(frozen=True)
class GeneratedQuestion:
    type: QuestionType
    text: str
    points: float
    options: tuple[GeneratedOption, ...] = ()
    rubric: GeneratedRubric | None = None


@dataclass(frozen=True)
class GeneratedTest:
    title: str
    questions: tuple[GeneratedQuestion, ...]

    def count(self, question_type: QuestionType) -> int:
        return sum(1 for question in self.questions if question.type is question_type)

    @property
    def closed_count(self) -> int:
        return self.count(QuestionType.closed)

    @property
    def open_count(self) -> int:
        return self.count(QuestionType.open)


def strip_code_fence(raw: str) -> str:
    content = raw.strip()
    if not content.startswith("```"):
        return content
    content = content.strip("`").strip()
    lines = content.splitlines()
    if lines and lines[0].strip().lower() in FENCE_LANGUAGES:
        lines = lines[1:]
    return "\n".join(lines).strip()


def parse_generated_test(raw: str) -> GeneratedTest:
    data = _load_object(raw)
    items = data.get("questions")
    if not isinstance(items, list) or not items:
        raise LLMResponseError("В ответе GigaChat нет вопросов")

    test = GeneratedTest(
        title=_parse_title(data.get("title")),
        questions=tuple(_parse_question(item) for item in items),
    )
    _validate_composition(test)
    return test


def _load_object(raw: str) -> dict:
    try:
        data = json.loads(strip_code_fence(raw))
    except json.JSONDecodeError as error:
        raise LLMResponseError(f"GigaChat вернул не JSON: {error}") from error
    if not isinstance(data, dict):
        raise LLMResponseError("GigaChat вернул JSON не в виде объекта")
    return data


def _parse_title(value: object) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return "Тест по материалу"


def _parse_question(item: object) -> GeneratedQuestion:
    if not isinstance(item, dict):
        raise LLMResponseError("Вопрос в ответе GigaChat описан не объектом")

    text = _require_text(item.get("text"), "В ответе GigaChat есть вопрос без текста")
    question_type = _parse_type(item.get("type"))
    points = _parse_points(item.get("points"))

    if question_type is QuestionType.closed:
        return GeneratedQuestion(
            type=question_type,
            text=text,
            points=points,
            options=_parse_options(item.get("options"), text),
        )
    return GeneratedQuestion(
        type=question_type,
        text=text,
        points=points,
        rubric=_parse_rubric(item.get("rubric"), text),
    )


def _parse_type(value: object) -> QuestionType:
    try:
        return QuestionType(value)
    except ValueError as error:
        raise LLMResponseError(f"Неизвестный тип вопроса: {value!r}") from error


def _parse_points(value: object) -> float:
    if value is None:
        return DEFAULT_POINTS
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise LLMResponseError(f"Баллы вопроса должны быть числом от 1 до 5: {value!r}")
    points = float(value)
    if not MIN_POINTS <= points <= MAX_POINTS:
        raise LLMResponseError(f"Баллы вопроса вне диапазона 1..5: {points}")
    return points


def _require_text(value: object, message: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LLMResponseError(message)
    return value.strip()


def _parse_options(raw: object, question_text: str) -> tuple[GeneratedOption, ...]:
    if not isinstance(raw, list):
        raise LLMResponseError(f"У закрытого вопроса нет списка вариантов: {question_text}")

    options: list[GeneratedOption] = []
    for item in raw:
        if not isinstance(item, dict):
            raise LLMResponseError(f"Вариант ответа описан не объектом: {question_text}")
        text = _require_text(item.get("text"), f"У варианта ответа нет текста: {question_text}")
        is_correct = item.get("is_correct")
        if not isinstance(is_correct, bool):
            raise LLMResponseError(f"У варианта ответа некорректный is_correct: {question_text}")
        options.append(GeneratedOption(text=text, is_correct=is_correct))

    if len(options) < MIN_CLOSED_OPTIONS:
        raise LLMResponseError(f"У закрытого вопроса меньше двух вариантов: {question_text}")
    if sum(option.is_correct for option in options) != 1:
        raise LLMResponseError(f"У закрытого вопроса должен быть ровно один правильный вариант: {question_text}")
    return tuple(options)


def _parse_rubric(raw: object, question_text: str) -> GeneratedRubric:
    if not isinstance(raw, dict):
        raise LLMResponseError(f"У открытого вопроса нет рубрики: {question_text}")

    criteria = _require_text(
        raw.get("criteria_text"),
        f"У открытого вопроса нет критериев: {question_text}",
    )
    reference = _require_text(
        raw.get("reference_answer"),
        f"У открытого вопроса нет эталонного ответа: {question_text}",
    )
    return GeneratedRubric(criteria_text=criteria, reference_answer=reference)


def _validate_composition(test: GeneratedTest) -> None:
    if test.closed_count != CLOSED_QUESTIONS_REQUIRED or test.open_count != OPEN_QUESTIONS_REQUIRED:
        raise LLMResponseError(
            "GigaChat вернул неверный состав теста: "
            f"{test.closed_count} закрытых и {test.open_count} открытых вместо "
            f"{CLOSED_QUESTIONS_REQUIRED} и {OPEN_QUESTIONS_REQUIRED}"
        )
