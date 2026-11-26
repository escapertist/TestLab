"""Проверка ответов: независимость элементов и проброс ошибок модели."""

import pytest

from testlab.errors import LLMError
from testlab.services.answers import AnswerToCheck, CheckService
from tests.helpers import FakeChecker


async def test_checks_each_answer():
    checker = FakeChecker(verdict=False)
    service = CheckService(checker)

    results = await service.check_answers(
        [AnswerToCheck("Вопрос 1", "Эталон 1", "Ответ 1"), AnswerToCheck("Вопрос 2", "Эталон 2", "")]
    )

    assert results == [False, False]
    assert checker.calls == [
        ("Вопрос 1", "Эталон 1", "Ответ 1"),
        ("Вопрос 2", "Эталон 2", ""),
    ]


async def test_error_propagates():
    service = CheckService(FakeChecker(error=LLMError("нет модели")))

    with pytest.raises(LLMError, match="нет модели"):
        await service.check_answers([AnswerToCheck("Вопрос", "Эталон", "Ответ")])
