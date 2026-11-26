"""Маршрут создания теста по материалу."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from testlab.dependencies.auth import CurrentTeacher
from testlab.dependencies.test import get_test_service
from testlab.schemas.material import TestOut
from testlab.schemas.test import TestCreateRequest
from testlab.services.test import TestService

router = APIRouter(prefix="/materials", tags=["tests"])


@router.post("/{material_id}/tests", response_model=TestOut, status_code=status.HTTP_201_CREATED)
async def create_test(
    material_id: UUID,
    service: Annotated[TestService, Depends(get_test_service)],
    user: CurrentTeacher,
    payload: TestCreateRequest | None = None,
) -> TestOut:
    test = await service.generate_for_material(
        teacher_id=user.id,
        material_id=str(material_id),
        title=payload.title if payload is not None else None,
    )
    return TestOut.model_validate(test)
