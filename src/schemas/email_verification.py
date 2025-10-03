from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class EmailVerificationCreate(BaseModel):
    email: EmailStr = Field(..., description="邮箱地址")
    purpose: str = Field(default="register", description="验证目的")


class EmailVerificationVerify(BaseModel):
    email: EmailStr = Field(..., description="邮箱地址")
    code: str = Field(..., description="验证码")
    purpose: str = Field(default="register", description="验证目的")


class EmailVerificationResponse(BaseModel):
    message: str = Field(..., description="响应消息")
    expires_at: datetime = Field(..., description="过期时间")

    class Config:
        from_attributes = True
