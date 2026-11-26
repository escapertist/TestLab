"""Схемы проверки ответов."""

from uuid import UUID

from pydantic import BaseModel, Field

MAX_ANSWERS = 20


class CheckItem(BaseModel):
    question_id: UUID
    question: str = Field(min_length=1)
    correct_answer: str = Field(min_length=1)
    user_answer: str


class CheckRequest(BaseModel):
    answers: list[CheckItem] = Field(min_length=1, max_length=MAX_ANSWERS)


class CheckResult(CheckItem):
    is_correct: bool


class CheckResponse(BaseModel):
    answers: list[CheckResult]
