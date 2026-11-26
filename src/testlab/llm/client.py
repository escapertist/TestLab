"""Клиент GigaChat: OAuth, запрос к модели и получение ответа."""

import uuid

import httpx

from testlab.config.llm_config import LLMConfig
from testlab.errors import LLMError
from testlab.llm.generation import GeneratedTest, parse_generated_test
from testlab.llm.prompt import SYSTEM_PROMPT, build_user_prompt

OAUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
CHAT_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"


class GigaChatClient:
    def __init__(self, config: LLMConfig, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._config = config
        self._transport = transport
        self._token: str | None = None

    async def generate_test(
        self,
        text: str,
        closed_count: int = 5,
        open_count: int = 2,
    ) -> GeneratedTest:
        payload = {
            "model": self._config.model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": build_user_prompt(
                        text[: self._config.max_input_chars],
                        closed_count,
                        open_count,
                    ),
                },
            ],
        }

        response = await self._post_chat(await self._get_token(), payload)
        if response.status_code == 401:
            # Токен мог истечь: перевыпускаем его и повторяем запрос один раз.
            self._token = None
            response = await self._post_chat(await self._get_token(), payload)
        if response.status_code == 401:
            raise LLMError("GigaChat отклонил авторизацию: проверьте GIGACHAT_CREDENTIALS")
        if response.status_code >= 400:
            raise LLMError(f"GigaChat вернул ошибку {response.status_code}")

        return parse_generated_test(self._message_content(response))

    async def _get_token(self) -> str:
        if self._token:
            return self._token
        if not self._config.credentials:
            raise LLMError("Не задан GIGACHAT_CREDENTIALS в .env")

        headers = {
            "Authorization": f"Basic {self._config.credentials}",
            "RqUID": str(uuid.uuid4()),
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }
        response = await self._post(OAUTH_URL, headers=headers, data={"scope": self._config.scope})
        if response.status_code >= 400:
            raise LLMError(f"Не удалось получить токен GigaChat: HTTP {response.status_code}")
        try:
            self._token = response.json()["access_token"]
        except (KeyError, ValueError) as error:
            raise LLMError(f"Не удалось получить токен GigaChat: {error}") from error
        return self._token

    async def _post_chat(self, token: str, payload: dict) -> httpx.Response:
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        return await self._post(CHAT_URL, headers=headers, json=payload)

    async def _post(self, url: str, **kwargs) -> httpx.Response:
        try:
            async with httpx.AsyncClient(
                transport=self._transport,
                verify=self._config.verify_ssl,
                timeout=self._config.timeout,
            ) as client:
                return await client.post(url, **kwargs)
        except httpx.HTTPError as error:
            raise LLMError(f"Ошибка запроса к GigaChat: {error}") from error

    @staticmethod
    def _message_content(response: httpx.Response) -> str:
        try:
            return response.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError) as error:
            raise LLMError(f"Неожиданный ответ GigaChat: {error}") from error
