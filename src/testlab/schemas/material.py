"""Схемы материалов и сгенерированных тестов."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from testlab.models.enums import QuestionType, TestStatus
from testlab.schemas.common import UtcDatetime


class ClosedOptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    text: str
    is_correct: bool
    order_index: int


class QuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: QuestionType
    text: str
    points: float
    order_index: int
    reference_answer: str | None = None
    options: list[ClosedOptionOut] = Field(default_factory=list)


class TestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    status: TestStatus
    generation_params: dict
    questions: list[QuestionOut] = Field(default_factory=list)


class MaterialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    filename: str
    is_uploaded: bool
    created_at: UtcDatetime


class MaterialDetailOut(MaterialOut):
    test: TestOut | None = None


class MaterialListOut(BaseModel):
    items: list[MaterialOut] = Field(default_factory=list)
    total: int
