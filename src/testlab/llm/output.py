"""Схемы структурированного ответа GigaChat."""

from pydantic import BaseModel, ConfigDict, Field

from testlab.models.enums import QuestionType


class Option(BaseModel):
    """Вариант ответа на закрытый вопрос."""

    text: str = Field(min_length=1, description="Текст варианта")
    is_correct: bool = Field(description="Верный ли вариант")


class Question(BaseModel):
    """Вопрос теста."""

    type: QuestionType = Field(description="Тип вопроса: open или closed")
    text: str = Field(min_length=1, description="Текст вопроса")
    options: list[Option] | None = Field(default=None, description="Варианты ответа, только у closed")
    reference_answer: str | None = Field(default=None, description="Эталонный ответ, только у open")


class Test(BaseModel):
    """Составить тест по учебному материалу."""

    model_config = ConfigDict(title="generate_test")

    title: str = Field(min_length=1, description="Название теста")
    questions: list[Question] = Field(description="Вопросы теста")


class Verdict(BaseModel):
    """Проверить ответ учащегося на вопрос."""

    model_config = ConfigDict(title="check_answer")

    is_correct: bool = Field(description="Верен ли ответ учащегося")
