# Здесь будет базовый класс для конфигов

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# .env ищется в корне проекта, а не относительно текущей рабочей папки
ENV_FILE = Path(__file__).resolve().parents[3] / ".env"

class BaseConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore"
    )