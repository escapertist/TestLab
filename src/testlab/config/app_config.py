"""Собранные настройки приложения."""

from pydantic import Field

from testlab.config.base_config import BaseConfig
from testlab.config.db_config import DatabaseConfig
from testlab.config.llm_config import LLMConfig


class AppConfig(BaseConfig):
    db: DatabaseConfig = Field(default_factory=DatabaseConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    uploads_dir: str = Field(default="uploads", description="Папка для загруженных PDF")
    uploads_max_bytes: int = Field(
        default=10 * 1024 * 1024,
        description="Максимальный размер загружаемого файла в байтах",
    )


settings = AppConfig()
