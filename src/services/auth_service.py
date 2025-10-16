from sqlalchemy.orm import Session
from src.config import settings
from src.core.auth import (create_access_token, create_refresh_token,
                           get_password_hash, verify_password, verify_token)
from src.core.exceptions import AuthenticationError, ValidationError
from src.core.redis import get_redis
from src.models.user import User
from src.schemas.user import (ForgotPasswordRequest, LoginResponse,
                              RegisterRequest, RegisterResponse, UserLogin,
                              UserResponse, UserRole)
from src.services.redis_verification_service import \
    RedisVerificationCodeService


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.verification_service = RedisVerificationCodeService()
        self.redis = get_redis()

    async def register(self, user_data: RegisterRequest) -> RegisterResponse:
        """用户注册"""
        # 验证邮箱验证码
        self.verification_service.verify_code(
            user_data.email,
            user_data.code,
            "register",
            user_data.session
        )

        # 检查邮箱是否已存在
        existing_user = self.db.query(User).filter(
            User.email == user_data.email).first()
        if existing_user:
            raise ValidationError("邮箱已存在")

        # 检查是否是第一个用户，如果是则设为管理员
        user_count = self.db.query(User).count()
        user_role = UserRole.admin if user_count == 0 else UserRole.organizer

        # 创建新用户
        hashed_password = get_password_hash(user_data.password)
        db_user = User(
            email=user_data.email,
            name=user_data.name,
            phone=user_data.phone,
            avatar=user_data.avatar,
            role=user_role,
            hashed_password=hashed_password
        )

        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)

        # 生成令牌
        access_token = create_access_token(data={"sub": str(db_user.id)})
        refresh_token = create_refresh_token(data={"sub": str(db_user.id)})

        # 返回注册响应
        user_response = UserResponse.model_validate(db_user)
        return RegisterResponse(
            user=user_response,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.access_token_expire_minutes * 60
        )

    async def login(self, user_data: UserLogin) -> LoginResponse:
        """User login"""
        # Verify user credentials
        user = self.db.query(User).filter(
            User.email == user_data.email).first()
        if not user or not verify_password(user_data.password, str(user.hashed_password)):
            raise AuthenticationError("Invalid email or password")

        if not bool(user.is_active):
            raise AuthenticationError("User account is disabled")

        # Generate token
        access_token = create_access_token(data={"sub": str(user.id)})

        # Return login response
        user_response = UserResponse.model_validate(user)
        return LoginResponse(token=access_token, user=user_response)

    async def get_current_user(self, token: str) -> UserResponse:
        """Get current user from token"""
        payload = verify_token(token)
        if not payload:
            raise AuthenticationError("Invalid token")

        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationError("Invalid token payload")

        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise AuthenticationError("User not found")

        return UserResponse.model_validate(user)

    async def refresh_token(self, token: str) -> str:
        """Refresh token"""
        # Verify the token
        payload = verify_token(token)
        if not payload:
            raise AuthenticationError("Invalid token")

        # Check if token is revoked
        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationError("Invalid token payload")

        revoked_key = f"revoked_token:{token}"
        if self.redis and self.redis.exists(revoked_key):
            raise AuthenticationError("Token has been revoked")

        # Generate new access token
        new_token = create_access_token(data={"sub": user_id})
        return new_token

    async def revoke_token(self, token: str) -> None:
        """Revoke token (logout)"""
        # Add token to revoked list in Redis
        payload = verify_token(token)
        if payload:
            # Store in Redis with expiration time matching token expiration
            exp = payload.get("exp")
            if exp and self.redis:
                import time

                ttl = exp - int(time.time())
                if ttl > 0:
                    revoked_key = f"revoked_token:{token}"
                    self.redis.setex(revoked_key, ttl, "1")

    async def reset_password(self, request: ForgotPasswordRequest) -> None:
        """Reset password"""
        # Verify email verification code
        self.verification_service.verify_code(
            request.email, request.code, "register", request.session
        )

        # Find user by email
        user = self.db.query(User).filter(User.email == request.email).first()
        if not user:
            raise ValidationError("User not found")

        # Update password
        hashed_password = get_password_hash(request.newPassword)
        setattr(user, "hashed_password", hashed_password)
        self.db.commit()
