"""Настройки GigaChat."""

from pydantic import Field
from pydantic_settings import SettingsConfigDict

from testlab.config.base_config import BaseConfig


class LLMConfig(BaseConfig):
    model_config = SettingsConfigDict(env_prefix="GIGACHAT_")

    credentials: str = Field(default="", description="client_id:secret в base64 из личного кабинета GigaChat")
    scope: str = Field(default="GIGACHAT_API_PERS", description="Область доступа для OAuth")
    model: str = Field(default="GigaChat", description="Название модели")
    verify_ssl: bool = Field(default=False, description="Проверять TLS-сертификат GigaChat")
    timeout: float = Field(default=60.0, description="Таймаут запроса в секундах")
    max_input_chars: int = Field(default=20000, description="Сколько символов материала отправлять в модель")
