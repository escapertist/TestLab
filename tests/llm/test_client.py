"""Транспорт GigaChat: успех, ретрай на 401, ошибки."""

import json

import httpx
import pytest

from testlab.config.llm_config import LLMConfig
from testlab.errors import LLMError
from testlab.llm.client import OAUTH_URL, GigaChatClient
from tests.helpers import build_llm_response


def make_config(**overrides) -> LLMConfig:
    values = {
        "credentials": "client:secret",
        "model": "GigaChat",
        "verify_ssl": False,
        "timeout": 5.0,
        "max_input_chars": 20000,
    }
    values.update(overrides)
    return LLMConfig(**values)


def chat_response() -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": build_llm_response()}}]})


async def test_generates_test():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url == OAUTH_URL:
            return httpx.Response(200, json={"access_token": "token-1"})
        return chat_response()

    client = GigaChatClient(make_config(), transport=httpx.MockTransport(handler))

    test = await client.generate_test("текст материала")

    assert test.closed_count == 5
    assert test.open_count == 2


async def test_retries_after_expired_token():
    calls = {"oauth": 0, "chat": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url == OAUTH_URL:
            calls["oauth"] += 1
            return httpx.Response(200, json={"access_token": f"token-{calls['oauth']}"})
        calls["chat"] += 1
        if calls["chat"] == 1:
            return httpx.Response(401, json={"message": "expired"})
        assert request.headers["Authorization"] == "Bearer token-2"
        return chat_response()

    client = GigaChatClient(make_config(), transport=httpx.MockTransport(handler))

    test = await client.generate_test("текст")

    assert calls == {"oauth": 2, "chat": 2}
    assert test.closed_count == 5


async def test_second_401_is_an_error():
    calls = {"oauth": 0, "chat": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url == OAUTH_URL:
            calls["oauth"] += 1
            return httpx.Response(200, json={"access_token": f"token-{calls['oauth']}"})
        calls["chat"] += 1
        return httpx.Response(401, json={"message": "denied"})

    client = GigaChatClient(make_config(), transport=httpx.MockTransport(handler))

    with pytest.raises(LLMError, match="авторизацию"):
        await client.generate_test("текст")
    assert calls == {"oauth": 2, "chat": 2}


async def test_timeout_is_an_error_without_secrets():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timeout", request=request)

    client = GigaChatClient(make_config(credentials="super-secret"), transport=httpx.MockTransport(handler))

    with pytest.raises(LLMError) as error:
        await client.generate_test("текст")

    assert "Ошибка запроса" in str(error.value)
    assert "super-secret" not in str(error.value)


async def test_model_error_status():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url == OAUTH_URL:
            return httpx.Response(200, json={"access_token": "token-1"})
        return httpx.Response(500, json={"message": "boom"})

    client = GigaChatClient(make_config(), transport=httpx.MockTransport(handler))

    with pytest.raises(LLMError, match="500"):
        await client.generate_test("текст")


async def test_unexpected_response_shape():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url == OAUTH_URL:
            return httpx.Response(200, json={"access_token": "token-1"})
        return httpx.Response(200, json={"unexpected": True})

    client = GigaChatClient(make_config(), transport=httpx.MockTransport(handler))

    with pytest.raises(LLMError, match="Неожиданный ответ"):
        await client.generate_test("текст")


async def test_missing_credentials():
    client = GigaChatClient(make_config(credentials=""), transport=httpx.MockTransport(lambda r: httpx.Response(500)))

    with pytest.raises(LLMError, match="GIGACHAT_CREDENTIALS"):
        await client.generate_test("текст")


async def test_input_is_truncated():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url == OAUTH_URL:
            return httpx.Response(200, json={"access_token": "token-1"})
        captured["payload"] = json.loads(request.content)
        return chat_response()

    client = GigaChatClient(make_config(max_input_chars=10), transport=httpx.MockTransport(handler))

    await client.generate_test("0123456789ABCDEF")

    prompt = captured["payload"]["messages"][-1]["content"]
    assert "0123456789" in prompt
    assert "ABCDEF" not in prompt
