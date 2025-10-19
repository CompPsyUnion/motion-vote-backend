"""基于Redis的验证码服务"""
import inspect
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union

from src.core.exceptions import BusinessError, ValidationError
from src.core.redis import get_redis
from src.utils.email_utils import EmailService


class VerificationCodeUtils:
    """基于Redis的邮箱验证码服务"""

    def __init__(self):
        self.redis = get_redis()
        self.email_service = EmailService()
        self.code_expire_minutes = 5  # 验证码有效期（分钟）
        self.resend_interval_seconds = 60  # 重发间隔（秒）
        self.max_attempts = 5  # 最大尝试次数

    def _get_code_key(self, email: str, purpose: str) -> str:
        """获取验证码Redis键"""
        return f"verification_code:{purpose}:{email}"

    def _get_session_key(self, session: str) -> str:
        """获取session Redis键"""
        return f"verification_session:{session}"

    def _get_rate_limit_key(self, email: str, purpose: str) -> str:
        """获取频率限制Redis键"""
        return f"verification_rate_limit:{purpose}:{email}"

    async def send_verification_code(self, email: str, purpose: str = "register") -> Dict[str, Union[bool, str]]:
        """发送验证码"""

        # 检查频率限制
        rate_limit_key = self._get_rate_limit_key(email, purpose)
        if self.redis.exists(rate_limit_key):
            ttl_result = self.redis.ttl(rate_limit_key)
            if inspect.isawaitable(ttl_result):
                ttl_result = await ttl_result
            ttl = int(ttl_result) if ttl_result and int(ttl_result) > 0 else 0
            raise ValidationError(f"请等待 {ttl} 秒后再重新发送验证码")

        # 生成验证码和session
        code = self.email_service.generate_verification_code()
        session = str(uuid.uuid4())

        # 准备存储数据
        verification_data = {
            "code": code,
            "email": email,
            "purpose": purpose,
            "session": session,
            "attempts": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=self.code_expire_minutes)).isoformat()
        }

        # 发送邮件
        email_result = await self.email_service.send_verification_code(email, code, purpose)

        if not email_result["success"]:
            raise BusinessError(f"验证码发送失败：{email_result['message']}")

        # 存储到Redis
        code_key = self._get_code_key(email, purpose)
        session_key = self._get_session_key(session)

        # 使用pipeline提高性能
        pipe = self.redis.pipeline()

        # 存储验证码数据（以email+purpose为键）
        pipe.setex(
            code_key,
            self.code_expire_minutes * 60,
            json.dumps(verification_data)
        )

        # 存储session映射（以session为键）
        pipe.setex(
            session_key,
            self.code_expire_minutes * 60,
            json.dumps({
                "email": email,
                "purpose": purpose,
                "code": code
            })
        )

        # 设置频率限制
        pipe.setex(rate_limit_key, self.resend_interval_seconds, "1")

        pipe.execute()

        return {
            "success": True,
            "message": "验证码已发送",
            "session": session
        }

    def verify_code(self, email: str, code: str, purpose: str, session: str) -> bool:
        """验证验证码"""

        # 验证session是否有效
        session_key = self._get_session_key(session)
        session_data_str = self.redis.get(session_key)

        if not session_data_str:
            raise ValidationError("无效的session或session已过期")

        try:
            session_data = json.loads(str(session_data_str))
        except (json.JSONDecodeError, TypeError):
            raise ValidationError("session数据格式错误")

        # 验证session中的email和purpose是否匹配
        if session_data.get("email") != email or session_data.get("purpose") != purpose:
            raise ValidationError("session与邮箱或用途不匹配")

        # 获取验证码数据
        code_key = self._get_code_key(email, purpose)
        verification_data_str = self.redis.get(code_key)

        if not verification_data_str:
            raise ValidationError("验证码不存在或已过期")

        try:
            verification_data = json.loads(str(verification_data_str))
        except (json.JSONDecodeError, TypeError):
            raise ValidationError("验证码数据格式错误")

        # 检查是否过期
        expires_at_str = verification_data.get("expires_at")
        if expires_at_str:
            expires_at = datetime.fromisoformat(
                expires_at_str.replace('Z', '+00:00'))
            if expires_at < datetime.now(timezone.utc):
                # 删除过期的验证码
                self.redis.delete(code_key)
                self.redis.delete(session_key)
                raise ValidationError("验证码已过期")

        # 检查尝试次数
        attempts = verification_data.get("attempts", 0)
        if attempts >= self.max_attempts:
            # 删除超过尝试次数的验证码
            self.redis.delete(code_key)
            self.redis.delete(session_key)
            raise ValidationError("验证码尝试次数过多，请重新获取")

        # 验证验证码
        stored_code = verification_data.get("code")
        if stored_code != code:
            # 增加尝试次数
            verification_data["attempts"] = attempts + 1

            # 检查是否达到最大尝试次数
            if verification_data["attempts"] >= self.max_attempts:
                # 删除验证码
                self.redis.delete(code_key)
                self.redis.delete(session_key)
                raise ValidationError("验证码尝试次数过多，请重新获取")
            else:
                # 更新尝试次数
                remaining_ttl = int(self.redis.ttl(
                    code_key) or 0)  # type: ignore
                if remaining_ttl > 0:
                    self.redis.setex(code_key, remaining_ttl,
                                     json.dumps(verification_data))
                raise ValidationError("验证码错误")

        # 验证成功，删除验证码和session
        self.redis.delete(code_key)
        self.redis.delete(session_key)

        return True

    def cleanup_expired_codes(self):
        """清理过期的验证码（Redis会自动过期，这里主要用于手动清理）"""
        # Redis的TTL机制会自动清理过期键，这个方法主要用于统计或手动清理
        pattern = "verification_code:*"
        keys = list(self.redis.keys(pattern))  # type: ignore

        expired_count = 0
        for key in keys:
            ttl = self.redis.ttl(key)
            if ttl == -2:  # 键不存在或已过期
                expired_count += 1

        return {"expired_count": expired_count}

    def get_verification_status(self, email: str, purpose: str) -> Optional[Dict[str, Any]]:
        """获取验证码状态（调试用）"""
        code_key = self._get_code_key(email, purpose)
        verification_data_str = self.redis.get(code_key)

        if not verification_data_str:
            return None

        try:
            verification_data = json.loads(str(verification_data_str))
            # 不返回实际验证码，只返回状态信息
            return {
                "email": verification_data.get("email"),
                "purpose": verification_data.get("purpose"),
                "attempts": verification_data.get("attempts", 0),
                "created_at": verification_data.get("created_at"),
                "expires_at": verification_data.get("expires_at"),
                "ttl": int(self.redis.ttl(code_key) or 0)  # type: ignore
            }
        except (json.JSONDecodeError, TypeError):
            return None
