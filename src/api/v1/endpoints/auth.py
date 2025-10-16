from datetime import datetime, timezone
from http import HTTPStatus

from fastapi import APIRouter, Depends, Query
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.schemas.base import ApiResponse
from src.schemas.email_verification import (EmailVerificationResponse,
                                            VerificationCodeData)
from src.schemas.user import (ForgotPasswordRequest, LoginResponse,
                              RefreshTokenResponse, RegisterRequest,
                              RegisterResponse, UserLogin)
from src.services.auth_service import AuthService
from src.services.redis_verification_service import \
    RedisVerificationCodeService

router = APIRouter()
security = HTTPBearer()


@router.get("/getcode", response_model=EmailVerificationResponse)
async def send_verification_code(email: str = Query(..., description="Email address")):
    """Send verification code to email"""
    verification_service = RedisVerificationCodeService()
    result = await verification_service.send_verification_code(email, "register")
    return EmailVerificationResponse(
        success=True,
        message=str(result["message"]),
        timestamp=datetime.now(timezone.utc),
        data=VerificationCodeData(session=str(result["session"])),
    )


@router.post("/register", response_model=RegisterResponse, status_code=HTTPStatus.CREATED)
async def register(user_data: RegisterRequest, db: Session = Depends(get_db)):
    """User registration"""
    auth_service = AuthService(db)
    return await auth_service.register(user_data)


@router.post("/login", response_model=LoginResponse)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """User login"""
    auth_service = AuthService(db)
    return await auth_service.login(user_data)


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(token=Depends(security), db: Session = Depends(get_db)):
    """Refresh JWT Token"""
    auth_service = AuthService(db)
    new_token = await auth_service.refresh_token(token.credentials)
    return RefreshTokenResponse(
        success=True,
        message="Token refreshed successfully",
        timestamp=datetime.now(timezone.utc),
        data={"token": new_token},
    )


@router.post("/revoke", response_model=ApiResponse)
async def revoke_token(token=Depends(security), db: Session = Depends(get_db)):
    """Revoke token (logout)"""
    auth_service = AuthService(db)
    await auth_service.revoke_token(token.credentials)
    return ApiResponse(
        success=True, message="Token revoked successfully", timestamp=datetime.now(timezone.utc)
    )


@router.post("/forgot-password", response_model=ApiResponse)
async def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Reset password"""
    auth_service = AuthService(db)
    await auth_service.reset_password(request)
    return ApiResponse(
        success=True,
        message="Password reset successfully",
        timestamp=datetime.now(timezone.utc),
    )
