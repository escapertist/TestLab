"""Бизнес-логика создания теста по материалу."""

from testlab.config.app_config import settings
from testlab.errors import ConflictError, NotFoundError, PersistenceError
from testlab.infrastructure.pdf import extract_text
from testlab.infrastructure.storage import FileStorage
from testlab.llm.client import TestGenerator
from testlab.llm.output import Question as OutputQuestion
from testlab.models.enums import QuestionType
from testlab.models.test import ClosedQuestionOption, Question, Test
from testlab.repositories.uow import UnitOfWork


class TestService:
    def __init__(self, uow: UnitOfWork, storage: FileStorage, llm: TestGenerator) -> None:
        self.uow = uow
        self.storage = storage
        self.llm = llm

    async def generate_for_material(
        self,
        teacher_id: str,
        material_id: str,
        title: str | None = None,
        *,
        closed_count: int,
        open_count: int,
        options_count: int,
    ) -> Test:
        material = await self.uow.materials.get_by_id_and_teacher(material_id, teacher_id)
        if material is None:
            raise NotFoundError("Материал не найден")
        if await self.uow.tests.get_by_material(material.id) is not None:
            raise ConflictError("Тест для материала уже создан")

        content = await self.storage.read(material.file_path)
        text = extract_text(content)
        generated = await self.llm.generate_test(
            text,
            closed_count=closed_count,
            open_count=open_count,
            options_count=options_count,
        )

        try:
            test = await self.uow.tests.create_with_questions(
                Test(
                    material_id=material.id,
                    teacher_id=teacher_id,
                    title=title or generated.title,
                    generation_params=self._generation_params(text, closed_count, open_count, options_count),
                ),
                self._build_questions(generated.questions),
            )
            await self.uow.commit()
        except Exception as error:
            await self.uow.rollback()
            raise PersistenceError("Не удалось сохранить тест") from error
        return test

    @staticmethod
    def _build_questions(questions: list[OutputQuestion]) -> list[Question]:
        built: list[Question] = []
        for index, item in enumerate(questions, start=1):
            question = Question(
                type=item.type,
                order_index=index,
                text=item.text,
            )
            # Обе связи выставляются явно: иначе сериализация ответа потянет
            # ленивую загрузку уже после коммита.
            if item.type is QuestionType.closed:
                question.options = [
                    ClosedQuestionOption(
                        text=option.text,
                        is_correct=option.is_correct,
                        order_index=option_index,
                    )
                    for option_index, option in enumerate(item.options or [], start=1)
                ]
                question.reference_answer = None
            else:
                question.options = []
                question.reference_answer = item.reference_answer
            built.append(question)
        return built

    @staticmethod
    def _generation_params(text: str, closed_count: int, open_count: int, options_count: int) -> dict:
        sent_chars = min(len(text), settings.llm.max_input_chars)
        return {
            "model": settings.llm.generation_model,
            "closed_count": closed_count,
            "open_count": open_count,
            "options_count": options_count,
            "text_chars": sent_chars,
            "text_truncated": len(text) > sent_chars,
        }
