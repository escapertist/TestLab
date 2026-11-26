"""Маршрут проверки ответов."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from testlab.dependencies.answers import get_check_service
from testlab.dependencies.auth import CurrentTeacher
from testlab.schemas.answers import CheckRequest, CheckResponse, CheckResult
from testlab.services.answers import AnswerToCheck, CheckService

router = APIRouter(prefix="/answers", tags=["answers"])


@router.post("/check", response_model=CheckResponse, status_code=status.HTTP_200_OK)
async def check_answers(
    payload: CheckRequest,
    service: Annotated[CheckService, Depends(get_check_service)],
    user: CurrentTeacher,
) -> CheckResponse:
    results = await service.check_answers(
        [
            AnswerToCheck(
                question=item.question,
                correct_answer=item.correct_answer,
                user_answer=item.user_answer,
            )
            for item in payload.answers
        ]
    )
    return CheckResponse(
        answers=[
            CheckResult(
                question_id=item.question_id,
                question=item.question,
                correct_answer=item.correct_answer,
                user_answer=item.user_answer,
                is_correct=is_correct,
            )
            for item, is_correct in zip(payload.answers, results, strict=True)
        ]
    )
