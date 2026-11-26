"""Схемы действий над тестом."""

from typing import Self

from pydantic import BaseModel, Field, model_validator

MAX_QUESTIONS = 20
MAX_OPTIONS = 10


class TestCreateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    closed_count: int = Field(default=5, ge=0, description="Сколько закрытых вопросов")
    open_count: int = Field(default=2, ge=0, description="Сколько открытых вопросов")
    options_count: int = Field(default=4, ge=2, le=MAX_OPTIONS, description="Сколько вариантов у закрытого вопроса")

    @model_validator(mode="after")
    def _check_total(self) -> Self:
        if not 1 <= self.closed_count + self.open_count <= MAX_QUESTIONS:
            raise ValueError(f"всего вопросов должно быть от 1 до {MAX_QUESTIONS}")
        return self
