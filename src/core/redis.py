"""Redis连接管理"""
from typing import Optional

import redis
from src.config import settings


class RedisClient:
    """Redis客户端单例"""
    _instance: Optional[redis.Redis] = None

    @classmethod
    def get_instance(cls) -> redis.Redis:
        """获取Redis实例"""
        if cls._instance is None:
            cls._instance = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
        # 类型检查：此时_instance不会为None
        assert cls._instance is not None
        return cls._instance

    @classmethod
    def close(cls):
        """关闭Redis连接"""
        if cls._instance:
            cls._instance.close()
            cls._instance = None


def get_redis() -> redis.Redis:
    """获取Redis客户端"""
    return RedisClient.get_instance()
