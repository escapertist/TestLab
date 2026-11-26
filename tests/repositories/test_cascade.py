"""Каскадное удаление через внешние ключи SQLite."""

from sqlalchemy import func, select

from testlab.models.enums import QuestionType
from testlab.models.material import Material
from testlab.models.test import ClosedQuestionOption, Question
from testlab.models.test import Test as OrmTest
from testlab.models.user import User
from testlab.repositories.uow import UnitOfWork


async def count(session, model) -> int:
    return int(await session.scalar(select(func.count()).select_from(model)) or 0)


async def test_delete_material_cascades(session_maker):
    async with session_maker() as session:
        uow = UnitOfWork(session)
        teacher = await uow.users.create(User(username="cascade", password_hash="x", full_name="Т"))
        material = await uow.materials.create(
            Material(teacher_id=teacher.id, title="M", file_path="p.pdf", filename="p.pdf")
        )
        await uow.tests.create_with_questions(
            OrmTest(material_id=material.id, teacher_id=teacher.id, title="T"),
            [
                Question(
                    type=QuestionType.closed,
                    order_index=1,
                    text="Закрытый",
                    points=1,
                    options=[ClosedQuestionOption(text="a", is_correct=True, order_index=1)],
                ),
                Question(
                    type=QuestionType.open,
                    order_index=2,
                    text="Открытый",
                    points=2,
                    reference_answer="r",
                ),
            ],
        )
        await uow.commit()

        assert await count(session, OrmTest) == 1
        assert await count(session, Question) == 2

        await uow.materials.delete(material)
        await uow.commit()

        assert await count(session, Material) == 0
        assert await count(session, OrmTest) == 0
        assert await count(session, Question) == 0
        assert await count(session, ClosedQuestionOption) == 0


async def test_questions_keep_order(session_maker):
    async with session_maker() as session:
        uow = UnitOfWork(session)
        teacher = await uow.users.create(User(username="order", password_hash="x", full_name="Т"))
        material = await uow.materials.create(
            Material(teacher_id=teacher.id, title="M", file_path="p.pdf", filename="p.pdf")
        )
        await uow.tests.create_with_questions(
            OrmTest(material_id=material.id, teacher_id=teacher.id, title="T"),
            [
                Question(type=QuestionType.open, order_index=2, text="Второй", points=1),
                Question(type=QuestionType.open, order_index=1, text="Первый", points=1),
            ],
        )
        await uow.commit()
        material_id = material.id

    async with session_maker() as session:
        test = await UnitOfWork(session).tests.get_by_material(material_id)

    assert test is not None
    assert [question.order_index for question in test.questions] == [1, 2]

