"""Провайдеры клиентов GigaChat."""

from functools import lru_cache

from testlab.config.app_config import settings
from testlab.llm.chat import check_client, generation_client
from testlab.llm.client import AnswerChecker, TestGenerator


@lru_cache
def get_generation_client() -> TestGenerator:
    return TestGenerator(generation_client(), settings.llm)


@lru_cache
def get_check_client() -> AnswerChecker:
    return AnswerChecker(check_client(), settings.llm)
