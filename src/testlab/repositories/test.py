"""Репозиторий тестов и вопросов."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from testlab.models.test import Question, Test


class TestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_with_questions(self, test: Test, questions: list[Question]) -> Test:
        test.questions.extend(questions)
        self.session.add(test)
        await self.session.flush()
        return test

    async def get_with_questions(self, test_id: str) -> Test | None:
        result = await self.session.execute(
            select(Test).where(Test.id == test_id).options(*_with_questions())
        )
        return result.scalar_one_or_none()

    async def get_by_material(self, material_id: str) -> Test | None:
        result = await self.session.execute(
            select(Test)
            .where(Test.material_id == material_id)
            .order_by(Test.created_at.desc())
            .limit(1)
            .options(*_with_questions())
        )
        return result.scalar_one_or_none()


def _with_questions():
    return (selectinload(Test.questions).selectinload(Question.options),)
