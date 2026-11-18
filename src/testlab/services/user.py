from uuid import uuid4
from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from testlab.schemas.user import UserLoginRequest, UserLoginResponse, UserRegisterRequest, UserRegisterResponse
from testlab.models.user import User
from testlab.repositories.user import UserRepository
from testlab.config.security import get_password_hash

class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    async def register(self, data: UserRegisterRequest) -> UserRegisterResponse:
        # Проверка, нет ли такого юзера уже
        existing_user = await self.repo.get_by_username(data.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким username уже существует"
            )

        # Хэшируем пароль
        hashed_password = get_password_hash(data.password)

        # Создаем модель БД
        new_user = User(
            username=data.username,
            password_hash=hashed_password,
            full_name=data.full_name,
            role=data.role
        )

        # Сохраняем
        saved_user = await self.repo.create(new_user)

        return UserRegisterResponse.model_validate(saved_user)

    async def login(self, username: str, password: str) -> UserLoginResponse:
        user = await self.repo.get_by_username(username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный логин и пароль"
            )

        user_out = UserRegisterResponse.model_validate(user)

        return UserLoginResponse(
            access_token="fake-jwt-token",
            token_type="bearer",
            user=user_out
        )