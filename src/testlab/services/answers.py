"""Бизнес-логика проверки ответов."""

from collections.abc import Sequence
from dataclasses import dataclass

from testlab.llm.client import AnswerChecker


@dataclass(frozen=True)
class AnswerToCheck:
    question: str
    correct_answer: str
    user_answer: str


class CheckService:
    def __init__(self, llm: AnswerChecker) -> None:
        self.llm = llm

    async def check_answers(self, answers: Sequence[AnswerToCheck]) -> list[bool]:
        results: list[bool] = []
        for answer in answers:
            results.append(
                await self.llm.check_answer(answer.question, answer.correct_answer, answer.user_answer)
            )
        return results
