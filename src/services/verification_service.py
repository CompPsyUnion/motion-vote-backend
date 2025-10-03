import uuid
from datetime import datetime, timedelta, timezone
from typing import cast

from sqlalchemy.orm import Session
from src.core.exceptions import BusinessError, ValidationError
from src.models.email_verification import EmailVerification
from src.services.email_service import EmailService


class VerificationCodeService:
    """验证码服务"""

    def __init__(self, db: Session):
        self.db = db
        self.email_service = EmailService()
        self.max_attempts = 5  # 最大验证尝试次数
        self.code_expire_minutes = 10  # 验证码过期时间（分钟）
        self.resend_interval_seconds = 60  # 重发间隔（秒）

    async def send_verification_code(self, email: str, purpose: str = "register") -> dict:
        """发送验证码"""

        # 检查是否有未过期的验证码
        existing_code = self.db.query(EmailVerification).filter(
            EmailVerification.email == email,
            EmailVerification.purpose == purpose,
            EmailVerification.used == False,
            EmailVerification.expires_at > datetime.now(
                timezone.utc).replace(tzinfo=None)
        ).first()

        if existing_code:
            # 检查重发间隔
            created_at = cast(datetime, getattr(existing_code, "created_at"))
            time_since_sent = datetime.now(
                timezone.utc).replace(tzinfo=None) - created_at
            if time_since_sent.total_seconds() < self.resend_interval_seconds:
                remaining_seconds = self.resend_interval_seconds - \
                    int(time_since_sent.total_seconds())
                raise ValidationError(f"请等待 {remaining_seconds} 秒后再重新发送验证码")

        # 生成新的验证码和session
        code = self.email_service.generate_verification_code()
        session = str(uuid.uuid4())
        expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + \
            timedelta(minutes=self.code_expire_minutes)

        # 发送邮件
        email_result = await self.email_service.send_verification_code(email, code, purpose)

        if not email_result["success"]:
            raise BusinessError(f"验证码发送失败：{email_result['message']}")

        # 删除旧的验证码记录
        self.db.query(EmailVerification).filter(
            EmailVerification.email == email,
            EmailVerification.purpose == purpose
        ).delete()

        # 保存新的验证码
        verification = EmailVerification(
            id=str(uuid.uuid4()),
            session=session,
            email=email,
            code=code,
            purpose=purpose,
            expires_at=expires_at
        )

        self.db.add(verification)
        self.db.commit()

        return {
            "message": "验证码已发送，请查收邮件",
            "session": session,
            "expires_at": expires_at
        }

    def verify_code(self, email: str, code: str, session: str, purpose: str = "register") -> bool:
        """验证验证码"""

        # 查找验证码记录
        verification = self.db.query(EmailVerification).filter(
            EmailVerification.email == email,
            EmailVerification.session == session,
            EmailVerification.purpose == purpose,
            EmailVerification.used == False
        ).first()

        if not verification:
            raise ValidationError("验证码不存在或已使用")

        # 检查是否过期
        expires_at = getattr(verification, "expires_at", None)
        if expires_at is not None and expires_at < datetime.now(timezone.utc).replace(tzinfo=None):
            raise ValidationError("验证码已过期")

        # 检查尝试次数 (将可能的 ORM 列值转换为 Python int 以供比较)
        attempts_value = cast(int, getattr(verification, "attempts", 0))
        if attempts_value >= self.max_attempts:
            raise ValidationError("验证码尝试次数过多，请重新获取")

        # 验证码错误 (将可能的 ORM 列值转换为 Python str 再比较)
        code_value = cast(str, getattr(verification, "code"))
        if code_value != code:
            # 使用 Python 值来递增并写回实例属性，使用 setattr 避开 ORM Column 类型的静态类型检查
            new_attempts = attempts_value + 1
            setattr(verification, "attempts", new_attempts)
            self.db.commit()
            remaining_attempts = self.max_attempts - new_attempts
            if remaining_attempts > 0:
                raise ValidationError(f"验证码错误，还可尝试 {remaining_attempts} 次")
            else:
                raise ValidationError("验证码尝试次数过多，请重新获取")

        # 验证成功，标记为已使用
        setattr(verification, "used", True)
        setattr(verification, "used_at", datetime.now(
            timezone.utc).replace(tzinfo=None))
        self.db.commit()

        return True

    def cleanup_expired_codes(self):
        """清理过期的验证码"""
        self.db.query(EmailVerification).filter(
            EmailVerification.expires_at < datetime.now(
                timezone.utc).replace(tzinfo=None)
        ).delete()
        self.db.commit()
