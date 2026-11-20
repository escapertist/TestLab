# Здесь будут конфиги базы данных

from pydantic import Field
from .base_config import BaseConfig

class DatabaseConfig(BaseConfig):
    url: str = Field(default="sqlite+aiosqlite:///./testlab.db", description="URL базы данных")
    echo: bool = Field(default=False, description="Выводить SQL в консоль")