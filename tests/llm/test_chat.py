"""Сборка клиентов GigaChat из настроек без сети."""

from langchain_gigachat import GigaChat

from testlab.config.llm_config import LLMConfig
from testlab.llm.chat import check_client, create_chat, generation_client


def test_create_chat_carries_config():
    config = LLMConfig(
        credentials="client:secret",
        scope="GIGACHAT_API_PERS",
        base_url="https://api.giga.chat/v1",
        timeout=5.0,
        verify_ssl=False,
    )

    chat = create_chat(config, "GigaChat-3-Ultra", 0.3)

    assert isinstance(chat, GigaChat)
    assert chat.model == "GigaChat-3-Ultra"
    assert chat.temperature == 0.3
    assert chat.base_url == "https://api.giga.chat/v1"
    assert chat.credentials == "client:secret"
    assert chat.scope == "GIGACHAT_API_PERS"
    assert chat.timeout == 5.0
    assert chat.verify_ssl_certs is False


def test_clients_are_built_without_network():
    assert generation_client() is not None
    assert check_client() is not None
