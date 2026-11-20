# Здесь будут все собранные настройки приложения

from pydantic import Field
from .base_config import BaseConfig
from .db_config import DatabaseConfig

class AppConfig(BaseConfig):
    db: DatabaseConfig = Field(default_factory=DatabaseConfig)
    # Позже добавим сюда security и llm

settings = AppConfig()