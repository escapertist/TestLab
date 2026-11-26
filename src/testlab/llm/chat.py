"""Создание клиентов GigaChat: по одному на роль, без фабрики."""

from langchain_core.runnables import Runnable
from langchain_gigachat import GigaChat

from testlab.config.app_config import settings
from testlab.config.llm_config import LLMConfig
from testlab.llm.output import Test, Verdict


def create_chat(config: LLMConfig, model: str, temperature: float) -> GigaChat:
    """Собирает модель GigaChat из настроек: параметры ролей отличаются только значениями."""
    return GigaChat(
        model=model,
        temperature=temperature,
        credentials=config.credentials,
        scope=config.scope,
        base_url=config.base_url,
        timeout=config.timeout,
        verify_ssl_certs=config.verify_ssl,
    )


def generation_client() -> Runnable:
    """Клиент генерации теста: структурированный вывод по схеме теста."""
    chat = create_chat(settings.llm, settings.llm.generation_model, settings.llm.generation_temperature)
    return chat.with_structured_output(Test)


def check_client() -> Runnable:
    """Клиент проверки ответа: структурированный вердикт `is_correct`."""
    chat = create_chat(settings.llm, settings.llm.check_model, settings.llm.check_temperature)
    return chat.with_structured_output(Verdict)
