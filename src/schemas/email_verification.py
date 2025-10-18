from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class EmailVerificationCreate(BaseModel):
    email: EmailStr = Field(..., description="邮箱地址")
    purpose: str = Field(default="register", description="验证目的")


class EmailVerificationVerify(BaseModel):
    email: EmailStr = Field(..., description="邮箱地址")
    code: str = Field(..., description="验证码")
    session: str = Field(..., description="验证码session")
    purpose: str = Field(default="register", description="验证目的")


class VerificationCodeData(BaseModel):
    session: str = Field(..., description="验证码对应的有效sessionid，用于验证验证码用途")


class EmailVerificationResponse(BaseModel):
    success: bool = Field(True, description="请求是否成功")
    message: str = Field(..., description="响应消息")
    timestamp: datetime = Field(..., description="响应时间戳")
    data: VerificationCodeData = Field(..., description="验证码数据")

    class Config:
        from_attributes = True
