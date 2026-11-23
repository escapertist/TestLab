from testlab.models.user import User
from testlab.repositories.user import UserRepository
from testlab.exceptions import UserAlreadyExistsError, InvalidCredentialsError
from testlab.schemas.user import UserRegisterRequest, UserRegisterResponse, UserLoginResponse

from testlab.security import get_password_hash, verify_password

class UserService:
    def __init__(self, db):
        self.repo = UserRepository(db)

    async def register(self, data: UserRegisterRequest) -> UserRegisterResponse:
        existing_user = await self.repo.get_by_username(data.username)
        if existing_user:
            raise UserAlreadyExistsError("Пользователь с таким username уже существует")
        
        new_user = User(
            username=data.username,
            password_hash=get_password_hash(data.password),
            full_name=data.full_name,
            role=data.role
        )
        saved_user = await self.repo.create(new_user)
        return UserRegisterResponse.model_validate(saved_user)

    async def login(self, username: str, password: str) -> UserLoginResponse:
        user = await self.repo.get_by_username(username)
        if not user:
            raise InvalidCredentialsError("Неверный логин или пароль")

        if not verify_password(password, user.password_hash):
            raise InvalidCredentialsError("Неверный логин или пароль")
        
        user_out = UserRegisterResponse.model_validate(user)
        return UserLoginResponse(
            access_token="fake-jwt-token",
            token_type="bearer",
            user=user_out
        )