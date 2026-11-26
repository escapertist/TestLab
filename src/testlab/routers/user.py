"""Маршруты /auth: регистрация, вход, текущий пользователь."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from testlab.dependencies.auth import CurrentUser
from testlab.dependencies.user import get_user_service
from testlab.schemas.user import (
    UserLoginRequest,
    UserLoginResponse,
    UserRegisterRequest,
    UserRegisterResponse,
)
from testlab.services.user import UserService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: UserRegisterRequest,
    service: Annotated[UserService, Depends(get_user_service)],
) -> UserRegisterResponse:
    user = await service.register(
        username=data.username,
        password=data.password,
        full_name=data.full_name,
        role=data.role,
    )
    return UserRegisterResponse.model_validate(user)


@router.post("/login", response_model=UserLoginResponse)
async def login(
    data: UserLoginRequest,
    service: Annotated[UserService, Depends(get_user_service)],
) -> UserLoginResponse:
    user = await service.login(data.username, data.password)
    profile = UserRegisterResponse.model_validate(user).model_dump()
    return UserLoginResponse(**profile, access_token=service.issue_token(user))


@router.get("/me", response_model=UserRegisterResponse)
async def me(user: CurrentUser) -> UserRegisterResponse:
    return UserRegisterResponse.model_validate(user)
