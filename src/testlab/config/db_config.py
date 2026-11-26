"""Настройки подключения к базе данных."""

from pydantic import Field
from pydantic_settings import SettingsConfigDict

from testlab.config.base_config import BaseConfig


class DatabaseConfig(BaseConfig):
    model_config = SettingsConfigDict(env_prefix="DB_")

    url: str = Field(default="sqlite+aiosqlite:///./testlab.db", description="URL базы данных")
    echo: bool = Field(default=False, description="Выводить SQL в консоль")
