from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class UserRole(str, Enum):
    admin = "admin"
    organizer = "organizer"
    empty = ""


class UserBase(BaseModel):
    email: str = Field(..., description="邮箱地址")
    name: str = Field(..., description="用户姓名")
    phone: Optional[str] = Field(None, description="手机号")
    avatar: Optional[str] = Field(None, description="头像URL")


class RegisterRequest(UserBase):
    password: str = Field(..., min_length=8, description="密码（8位以上，包含字母数字）")
    code: str = Field(..., description="邮箱验证码")
    session: str = Field(..., description="邮箱验证码session")


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, description="用户姓名")
    phone: Optional[str] = Field(None, description="手机号")
    avatar: Optional[str] = Field(None, description="头像URL")
    role: Optional[UserRole] = Field(None, description="用户角色（仅管理员可修改）")


class UserResponse(UserBase):
    id: str = Field(..., description="用户ID")
    role: UserRole = Field(..., description="用户角色")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    email: str = Field(..., description="邮箱地址")
    password: str = Field(..., description="密码")


class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., description="Email address")
    code: str = Field(..., description="Verification code")
    session: str = Field(..., description="Verification session")
    newPassword: str = Field(..., min_length=6,
                             description="New password", alias="newPassword")

    class Config:
        populate_by_name = True
