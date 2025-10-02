from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class UserRole(str, Enum):
    admin = "admin"
    organizer = "organizer"


class UserBase(BaseModel):
    email: str = Field(..., description="邮箱地址")
    name: str = Field(..., description="用户姓名")
    phone: Optional[str] = Field(None, description="手机号")
    avatar: Optional[str] = Field(None, description="头像URL")


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="密码（8位以上，包含字母数字）")


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, description="用户姓名")
    phone: Optional[str] = Field(None, description="手机号")
    avatar: Optional[str] = Field(None, description="头像URL")


class UserResponse(UserBase):
    id: str = Field(..., description="用户ID")
    role: UserRole = Field(..., description="用户角色")
    created_at: datetime = Field(..., alias="createdAt", description="创建时间")
    updated_at: datetime = Field(..., alias="updatedAt", description="更新时间")

    class Config:
        from_attributes = True
        populate_by_name = True


class UserLogin(BaseModel):
    email: str = Field(..., description="邮箱地址")
    password: str = Field(..., description="密码")


class TokenResponse(BaseModel):
    access_token: str = Field(..., alias="accessToken", description="访问令牌")
    refresh_token: str = Field(..., alias="refreshToken", description="刷新令牌")
    token_type: str = Field(
        default="bearer", alias="tokenType", description="令牌类型")
    expires_in: int = Field(..., alias="expiresIn", description="令牌有效期（秒）")

    class Config:
        populate_by_name = True


class PasswordReset(BaseModel):
    email: str = Field(..., description="邮箱地址")
