# Здесь будут конфиги базы данных

from pydantic import Field
from .base_config import BaseConfig
from pydantic_settings import SettingsConfigDict

class DatabaseConfig(BaseConfig):

    model_config = SettingsConfigDict(env_prefix="DB_")
    
    url: str = Field(default="sqlite+aiosqlite:///./testlab.db", description="URL базы данных")
    echo: bool = Field(default=False, description="Выводить SQL в консоль")