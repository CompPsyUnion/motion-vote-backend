from sqlalchemy.orm import Session
from src.config import settings
from src.core.auth import (create_access_token, create_refresh_token,
                           get_password_hash, verify_password)
from src.core.exceptions import (AuthenticationError, BusinessError,
                                 ValidationError)
from src.models.user import User
from src.schemas.user import (RegisterRequest, RegisterResponse, TokenResponse,
                              UserCreate, UserLogin, UserResponse, UserRole)
from src.services.redis_verification_service import \
    RedisVerificationCodeService


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.verification_service = RedisVerificationCodeService()

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

    async def login(self, user_data: UserLogin) -> TokenResponse:
        """用户登录"""
        # 验证用户凭据
        user = self.db.query(User).filter(
            User.email == user_data.email).first()
        if not user or not verify_password(user_data.password, str(user.hashed_password)):
            raise AuthenticationError("邮箱或密码错误")

        if not bool(user.is_active):
            raise AuthenticationError("用户账号已被禁用")

        # 生成令牌
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.access_token_expire_minutes * 60
        )

    async def refresh_token(self, refresh_token: str) -> TokenResponse:
        """刷新令牌"""
        # 这里需要实现刷新令牌的逻辑
        raise BusinessError("刷新令牌功能尚未实现")

    async def forgot_password(self, email: str) -> None:
        """忘记密码"""
        # 这里需要实现发送密码重置邮件的逻辑
        raise BusinessError("密码重置功能尚未实现")
