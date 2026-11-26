"""Схемы регистрации, входа и профиля."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from testlab.models.enums import UserRole
from testlab.schemas.common import UtcDatetime


class UserRegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=255)
    role: UserRole = UserRole.student


class UserLoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class UserRegisterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    full_name: str
    role: UserRole
    created_at: UtcDatetime


class UserLoginResponse(UserRegisterResponse):
    access_token: str
    token_type: str = "bearer"
