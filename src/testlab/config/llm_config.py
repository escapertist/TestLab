"""Настройки GigaChat."""

from pydantic import Field
from pydantic_settings import SettingsConfigDict

from testlab.config.base_config import BaseConfig

GIGACHAT_BASE_URL = "https://api.giga.chat/v1"
GIGACHAT_SCOPE = "GIGACHAT_API_PERS"
GIGACHAT_MODEL = "GigaChat-3-Ultra"


class LLMConfig(BaseConfig):
    model_config = SettingsConfigDict(env_prefix="GIGACHAT_")

    credentials: str = Field(default="", description="client_id:secret в base64 из личного кабинета GigaChat")
    scope: str = Field(default=GIGACHAT_SCOPE, description="Область доступа для OAuth")
    base_url: str = Field(default=GIGACHAT_BASE_URL, description="Базовый адрес GigaChat API")
    verify_ssl: bool = Field(default=False, description="Проверять TLS-сертификат GigaChat")
    timeout: float = Field(default=60.0, description="Таймаут запроса в секундах")
    max_input_chars: int = Field(default=20000, description="Сколько символов материала отправлять в модель")
    generation_model: str = Field(default=GIGACHAT_MODEL, description="Модель для генерации теста")
    generation_temperature: float = Field(default=0.2, description="Температура генерации теста")
    check_model: str = Field(default=GIGACHAT_MODEL, description="Модель для проверки ответов")
    check_temperature: float = Field(default=0.0, description="Температура проверки ответов")
