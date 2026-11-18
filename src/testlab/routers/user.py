# Здесь будут эндпоинты

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from testlab.config.db import get_db
from testlab.services.user import UserService
from testlab.schemas.user import UserRegisterResponse, UserRegisterRequest, UserLoginRequest, UserLoginResponse
from testlab.dependencies.user import get_user_service

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post(
    "/register",
    response_model=UserRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация нового пользователя"
)
async def register(
    data: UserRegisterRequest,
    service: UserService = Depends(get_user_service)
):
    return await service.register(data)

@router.post(
    "/login",
    response_model=UserLoginResponse,
    summary="Аутентификация и получение токена"
)
async def login(
    data: UserLoginRequest,
    service: UserService = Depends(get_user_service)
):
    return await service.login(data.username, data.password)