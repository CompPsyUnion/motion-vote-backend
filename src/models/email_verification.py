from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from src.core.database import Base


class EmailVerification(Base):
    """邮箱验证码表"""
    __tablename__ = "email_verifications"

    id = Column(String, primary_key=True, index=True)
    email = Column(String, nullable=False, index=True)
    code = Column(String, nullable=False)
    # register, reset_password
    purpose = Column(String, nullable=False, default="register")
    used = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    used_at = Column(DateTime, nullable=True)
    attempts = Column(Integer, default=0)  # 验证尝试次数
