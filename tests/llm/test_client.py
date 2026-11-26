"""Адаптеры GigaChat: структурированный вызов, проверка состава и ошибки."""

import pytest
from gigachat.exceptions import GigaChatException
from langchain_core.exceptions import OutputParserException
from pydantic import ValidationError

from testlab.config.llm_config import LLMConfig
from testlab.errors import LLMError, LLMResponseError
from testlab.llm.client import AnswerChecker, TestGenerator
from testlab.llm.output import Test, Verdict
from tests.helpers import build_generated_test


def make_config(**overrides) -> LLMConfig:
    values = {
        "credentials": "client:secret",
        "base_url": "https://api.giga.chat/v1",
        "max_input_chars": 20000,
    }
    values.update(overrides)
    return LLMConfig(**values)


class FakeChain:
    def __init__(self, result=None, error: Exception | None = None) -> None:
        self._result = result
        self._error = error
        self.messages = None

    async def ainvoke(self, messages, config=None, **kwargs):
        self.messages = messages
        if self._error is not None:
            raise self._error
        return self._result


def make_validation_error() -> ValidationError:
    with pytest.raises(ValidationError) as error:
        Test(title="", questions=[])
    return error.value


async def test_generates_test():
    chain = FakeChain(build_generated_test(closed=4, open_=3, options_count=4))
    generator = TestGenerator(chain, make_config())

    test = await generator.generate_test("текст материала", closed_count=4, open_count=3, options_count=4)

    assert len(test.questions) == 7
    assert test.questions[0].options is not None
    assert len(test.questions[0].options) == 4


async def test_wrong_composition_is_an_error():
    chain = FakeChain(build_generated_test(closed=4, open_=2, options_count=4))
    generator = TestGenerator(chain, make_config())

    with pytest.raises(LLMResponseError, match="состав"):
        await generator.generate_test("текст", closed_count=5, open_count=2, options_count=4)


async def test_wrong_options_count_is_an_error():
    chain = FakeChain(build_generated_test(closed=5, open_=2, options_count=2))
    generator = TestGenerator(chain, make_config())

    with pytest.raises(LLMResponseError, match="вариантов"):
        await generator.generate_test("текст", closed_count=5, open_count=2, options_count=4)


async def test_two_correct_options_is_an_error():
    test = build_generated_test(closed=5, open_=2, options_count=4)
    assert test.questions[0].options is not None
    test.questions[0].options[1].is_correct = True
    generator = TestGenerator(FakeChain(test), make_config())

    with pytest.raises(LLMResponseError, match="ровно один"):
        await generator.generate_test("текст", closed_count=5, open_count=2, options_count=4)


async def test_missing_reference_answer_is_an_error():
    test = build_generated_test(closed=5, open_=2, options_count=4)
    test.questions[-1].reference_answer = None
    generator = TestGenerator(FakeChain(test), make_config())

    with pytest.raises(LLMResponseError, match="эталон"):
        await generator.generate_test("текст", closed_count=5, open_count=2, options_count=4)


async def test_validation_error_is_mapped():
    generator = TestGenerator(FakeChain(error=make_validation_error()), make_config())

    with pytest.raises(LLMResponseError, match="некорректный тест"):
        await generator.generate_test("текст", closed_count=5, open_count=2, options_count=4)


async def test_output_parser_error_is_mapped():
    generator = TestGenerator(FakeChain(error=OutputParserException("bad")), make_config())

    with pytest.raises(LLMResponseError, match="некорректный тест"):
        await generator.generate_test("текст", closed_count=5, open_count=2, options_count=4)


async def test_model_error_is_mapped():
    generator = TestGenerator(FakeChain(error=GigaChatException("boom")), make_config())

    with pytest.raises(LLMError, match="GigaChat не ответил"):
        await generator.generate_test("текст", closed_count=5, open_count=2, options_count=4)


async def test_missing_credentials():
    generator = TestGenerator(FakeChain(build_generated_test()), make_config(credentials=""))
    with pytest.raises(LLMError, match="GIGACHAT_CREDENTIALS"):
        await generator.generate_test("текст", closed_count=5, open_count=2, options_count=4)


async def test_input_is_truncated():
    chain = FakeChain(build_generated_test(options_count=4))
    generator = TestGenerator(chain, make_config(max_input_chars=10))

    await generator.generate_test("0123456789ABCDEF", closed_count=5, open_count=2, options_count=4)

    prompt = chain.messages[-1].content
    assert "0123456789" in prompt
    assert "ABCDEF" not in prompt


async def test_check_answer_returns_verdict():
    checker = AnswerChecker(FakeChain(Verdict(is_correct=True)), make_config())

    assert await checker.check_answer("вопрос", "эталон", "ответ") is True


async def test_check_answer_returns_false():
    checker = AnswerChecker(FakeChain(Verdict(is_correct=False)), make_config())

    assert await checker.check_answer("вопрос", "эталон", "ответ") is False


async def test_check_prompt_contains_answers():
    chain = FakeChain(Verdict(is_correct=True))
    checker = AnswerChecker(chain, make_config())

    await checker.check_answer("Что такое X?", "X — это Y", "X — это Z")

    prompt = chain.messages[-1].content
    assert "Что такое X?" in prompt
    assert "X — это Y" in prompt
    assert "X — это Z" in prompt
