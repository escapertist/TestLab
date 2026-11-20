# Здесь будут эндпоинты

from fastapi import APIRouter, Depends, HTTPException, status
from testlab.services.user import UserService
from testlab.dependencies.user import get_user_service
from testlab.exceptions import UserAlreadyExistsError, InvalidCredentialsError
from testlab.schemas.user import UserRegisterResponse, UserRegisterRequest, UserLoginRequest, UserLoginResponse

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserRegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UserRegisterRequest, service: UserService = Depends(get_user_service)):
    try:
        return await service.register(data)
    except UserAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/login", response_model=UserLoginResponse)
async def login(data: UserLoginRequest, service: UserService = Depends(get_user_service)):
    try:
        return await service.login(data.username, data.password)
    except InvalidCredentialsError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))