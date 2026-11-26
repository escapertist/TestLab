"""Адаптеры GigaChat: промпт, структурированный вызов и маппинг ошибок."""

from typing import Any

from gigachat.exceptions import GigaChatException
from langchain_core.exceptions import OutputParserException
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import Runnable
from pydantic import ValidationError

from testlab.config.llm_config import LLMConfig
from testlab.errors import LLMError, LLMResponseError
from testlab.llm.output import Test
from testlab.llm.prompt import SYSTEM_PROMPT, build_check_prompt, build_generation_prompt
from testlab.models.enums import QuestionType


class TestGenerator:
    """Генерация теста по тексту материала через структурированный ответ модели."""

    def __init__(self, chain: Runnable, config: LLMConfig) -> None:
        self._chain = chain
        self._config = config

    async def generate_test(
        self,
        text: str,
        *,
        closed_count: int,
        open_count: int,
        options_count: int,
    ) -> Test:
        _require_credentials(self._config)
        prompt = build_generation_prompt(
            text[: self._config.max_input_chars],
            closed_count,
            open_count,
            options_count,
        )
        test = await _call(self._chain, prompt, "GigaChat вернул некорректный тест")
        if test is None:
            raise LLMResponseError("GigaChat не вернул тест")
        _ensure_counts(test, closed_count, open_count, options_count)
        return test


class AnswerChecker:
    """Проверка одного ответа учащегося через структурированный вердикт модели."""

    def __init__(self, chain: Runnable, config: LLMConfig) -> None:
        self._chain = chain
        self._config = config

    async def check_answer(self, question: str, correct_answer: str, user_answer: str) -> bool:
        _require_credentials(self._config)
        prompt = build_check_prompt(question, correct_answer, user_answer)
        verdict = await _call(self._chain, prompt, "GigaChat вернул некорректный вердикт")
        if verdict is None:
            raise LLMResponseError("GigaChat не вернул вердикт")
        return verdict.is_correct


async def _call(chain: Runnable, prompt: str, response_error: str) -> Any:
    messages = [SystemMessage(SYSTEM_PROMPT), HumanMessage(prompt)]
    try:
        return await chain.ainvoke(messages)
    except (ValidationError, OutputParserException) as error:
        raise LLMResponseError(response_error) from error
    except GigaChatException as error:
        raise LLMError(f"GigaChat не ответил: {error}") from error


def _require_credentials(config: LLMConfig) -> None:
    if not config.credentials:
        raise LLMError("Не задан GIGACHAT_CREDENTIALS в .env")


def _ensure_counts(test: Test, closed_count: int, open_count: int, options_count: int) -> None:
    closed = [item for item in test.questions if item.type is QuestionType.closed]
    open_ = [item for item in test.questions if item.type is QuestionType.open]

    if len(closed) != closed_count or len(open_) != open_count:
        raise LLMResponseError(
            "GigaChat вернул неверный состав теста: "
            f"{len(closed)} закрытых и {len(open_)} открытых вместо {closed_count} и {open_count}"
        )
    for item in closed:
        options = item.options or []
        if len(options) != options_count:
            raise LLMResponseError(f"У закрытого вопроса не {options_count} вариантов: {item.text}")
        if sum(option.is_correct for option in options) != 1:
            raise LLMResponseError(f"У закрытого вопроса должен быть ровно один правильный вариант: {item.text}")
    for item in open_:
        if not item.reference_answer:
            raise LLMResponseError(f"У открытого вопроса нет эталонного ответа: {item.text}")
