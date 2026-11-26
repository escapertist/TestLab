"""Провайдер сервиса проверки ответов."""

from fastapi import Depends

from testlab.dependencies.llm import get_check_client
from testlab.llm.client import AnswerChecker
from testlab.services.answers import CheckService


def get_check_service(llm: AnswerChecker = Depends(get_check_client)) -> CheckService:
    return CheckService(llm)
