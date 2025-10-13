from typing import Any, Dict

from src.services.redis_verification_service import RedisVerificationCodeService


class VerificationCodeService:
    """验证码服务（使用 Redis 存储，不再使用数据库表）

    这个类保留原有接口以兼容调用方，但内部委托给 `RedisVerificationCodeService`。
    """

    def __init__(self, db=None):
        # 保持构造签名兼容：旧代码会传入 db 会话，但现在不需要
        self._redis_service = RedisVerificationCodeService()

    async def send_verification_code(self, email: str, purpose: str = "register") -> Dict[str, Any]:
        """发送验证码，返回与之前兼容的数据结构"""
        return await self._redis_service.send_verification_code(email, purpose)

    def verify_code(self, email: str, code: str, session: str, purpose: str = "register") -> bool:
        """验证验证码，返回 True/抛出 ValidationError"""
        return self._redis_service.verify_code(email, code, purpose, session)

    def cleanup_expired_codes(self):
        """清理过期验证码（Redis 自动过期，但保留方法以兼容调用）"""
        return self._redis_service.cleanup_expired_codes()
