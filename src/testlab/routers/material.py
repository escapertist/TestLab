"""Маршруты /materials: загрузка, список, карточка, файл, удаление."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status
from fastapi.responses import FileResponse

from testlab.dependencies.auth import CurrentTeacher
from testlab.dependencies.material import get_material_service
from testlab.schemas.material import MaterialDetailOut, MaterialListOut, MaterialOut, TestOut
from testlab.services.material import MaterialService

router = APIRouter(prefix="/materials", tags=["materials"])


@router.post("", response_model=MaterialOut, status_code=status.HTTP_201_CREATED)
async def create_material(
    title: Annotated[str, Form(min_length=1, max_length=255)],
    file: Annotated[UploadFile, File()],
    service: Annotated[MaterialService, Depends(get_material_service)],
    user: CurrentTeacher,
) -> MaterialOut:
    content = await file.read()
    material = await service.upload_pdf(
        teacher_id=user.id,
        title=title,
        filename=file.filename or "material.pdf",
        content_type=file.content_type,
        content=content,
    )
    return MaterialOut.model_validate(material)


@router.get("", response_model=MaterialListOut)
async def list_materials(
    service: Annotated[MaterialService, Depends(get_material_service)],
    user: CurrentTeacher,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> MaterialListOut:
    items, total = await service.list_materials(user.id, limit, offset)
    return MaterialListOut(
        items=[MaterialOut.model_validate(item) for item in items],
        total=total,
    )


@router.get("/{material_id}", response_model=MaterialDetailOut)
async def get_material(
    material_id: UUID,
    service: Annotated[MaterialService, Depends(get_material_service)],
    user: CurrentTeacher,
) -> MaterialDetailOut:
    material, test = await service.get_material(user.id, str(material_id))
    return MaterialDetailOut(
        **MaterialOut.model_validate(material).model_dump(),
        test=TestOut.model_validate(test) if test is not None else None,
    )


@router.get("/{material_id}/file", response_class=FileResponse)
async def download_material_file(
    material_id: UUID,
    service: Annotated[MaterialService, Depends(get_material_service)],
    user: CurrentTeacher,
) -> FileResponse:
    material, path = await service.get_material_file(user.id, str(material_id))
    return FileResponse(path, media_type="application/pdf", filename=material.filename)


@router.delete("/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_material(
    material_id: UUID,
    service: Annotated[MaterialService, Depends(get_material_service)],
    user: CurrentTeacher,
) -> Response:
    await service.delete_material(user.id, str(material_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
