from http import HTTPStatus

from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.schemas.base import ApiResponse
from src.schemas.email_verification import EmailVerificationResponse
from src.schemas.user import (PasswordReset, RegisterResponse, TokenResponse,
                              UserCreate, UserLogin)
from src.services.auth_service import AuthService
from src.services.verification_service import VerificationCodeService

router = APIRouter()
security = HTTPBearer()


@router.get("/getcode", response_model=EmailVerificationResponse)
async def get_verification_code(
    email: str,
    db: Session = Depends(get_db)
):
    """获取验证码"""
    verification_service = VerificationCodeService(db)
    result = await verification_service.send_verification_code(email, "register")
    return EmailVerificationResponse(
        message=result["message"],
        expires_at=result["expires_at"]
    )


@router.post("/register", response_model=RegisterResponse, status_code=HTTPStatus.CREATED)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """用户注册"""
    auth_service = AuthService(db)
    return await auth_service.register(user_data)


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
