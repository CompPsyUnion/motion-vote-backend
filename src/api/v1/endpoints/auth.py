from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from http import HTTPStatus

from src.core.database import get_db
from src.schemas.user import UserCreate, UserLogin, TokenResponse, PasswordReset
from src.schemas.base import ApiResponse
from src.services.auth_service import AuthService

router = APIRouter()
security = HTTPBearer()


@router.post("/register", response_model=ApiResponse, status_code=HTTPStatus.CREATED)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """用户注册"""
    auth_service = AuthService(db)
    await auth_service.register(user_data)
    return ApiResponse(message="注册成功")


@router.post("/login", response_model=TokenResponse)
async def login(
    user_data: UserLogin,
    db: Session = Depends(get_db)
):
    """用户登录"""
    auth_service = AuthService(db)
    return await auth_service.login(user_data)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    token=Depends(security),
    db: Session = Depends(get_db)
):
    """刷新Token"""
    auth_service = AuthService(db)
    return await auth_service.refresh_token(token.credentials)


@router.post("/forgot-password", response_model=ApiResponse)
async def forgot_password(
    password_reset: PasswordReset,
    db: Session = Depends(get_db)
):
    """忘记密码"""
    auth_service = AuthService(db)
    await auth_service.forgot_password(password_reset.email)
    return ApiResponse(message="密码重置邮件已发送")
