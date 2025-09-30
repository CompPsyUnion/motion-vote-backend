from sqlalchemy.orm import Session
from typing import Optional
from src.models.user import User
from src.schemas.user import UserCreate, UserLogin, UserUpdate, TokenResponse
from src.core.auth import verify_password, get_password_hash, create_access_token, create_refresh_token
from src.core.exceptions import AuthenticationError, ValidationError, BusinessError
from datetime import timedelta
from src.config import settings


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    async def register(self, user_data: UserCreate) -> User:
        """用户注册"""
        # 检查邮箱是否已存在
        existing_user = self.db.query(User).filter(
            User.email == user_data.email).first()
        if existing_user:
            raise ValidationError("邮箱已存在")

        # 创建新用户
        hashed_password = get_password_hash(user_data.password)
        db_user = User(
            email=user_data.email,
            name=user_data.name,
            phone=user_data.phone,
            avatar=user_data.avatar,
            hashed_password=hashed_password
        )

        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)

        return db_user

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
