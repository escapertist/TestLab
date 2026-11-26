"""Схемы действий над тестом."""

from pydantic import BaseModel, Field


class TestCreateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
