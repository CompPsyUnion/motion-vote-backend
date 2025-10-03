"""Redis验证码管理工具"""
import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from src.core.redis import get_redis
from src.services.redis_verification_service import \
    RedisVerificationCodeService


class RedisVerificationManager:
    """Redis验证码管理器"""

    def __init__(self):
        self.redis = get_redis()
        self.service = RedisVerificationCodeService()

    def list_all_verification_codes(self) -> List[Dict[str, Any]]:
        """列出所有验证码"""
        pattern = "verification_code:*"
        try:
            keys = list(self.redis.keys(pattern))  # type: ignore

            codes = []
            for key in keys:
                data_str = self.redis.get(key)
                if data_str:
                    try:
                        data = json.loads(str(data_str))
                        ttl = self.redis.ttl(key)
                        ttl_value = int(ttl) if ttl is not None and int(ttl) > 0 else 0  # type: ignore
                        codes.append({
                            "key": str(key),
                            "email": data.get("email"),
                            "purpose": data.get("purpose"),
                            "session": data.get("session"),
                            "attempts": data.get("attempts", 0),
                            "created_at": data.get("created_at"),
                            "expires_at": data.get("expires_at"),
                            "ttl": ttl_value
                        })
                    except (json.JSONDecodeError, ValueError):
                        continue

            return codes
        except Exception as e:
            print(f"Error listing verification codes: {e}")
            return []

    def cleanup_all_verification_data(self) -> Dict[str, int]:
        """清理所有验证码相关数据"""
        patterns = [
            "verification_code:*",
            "verification_session:*",
            "verification_rate_limit:*"
        ]

        deleted_count = 0
        for pattern in patterns:
            try:
                keys = list(self.redis.keys(pattern))  # type: ignore
                if keys:
                    # type: ignore
                    result = self.redis.delete(*keys)
                    if hasattr(result, "__await__"):
                        import asyncio
                        loop = asyncio.get_event_loop()
                        result = loop.run_until_complete(result)
                    if isinstance(result, (list, tuple)):
                        deleted_count += sum(int(r) for r in result if r is not None and isinstance(r, (int, float, str)))
                    elif isinstance(result, (int, float, str)):
                        deleted_count += int(result)
                    else:
                        # If result is not convertible, skip
                        pass
            except Exception as e:
                print(f"Error deleting pattern {pattern}: {e}")

        return {"deleted_count": deleted_count}

    def get_stats(self) -> Dict[str, Any]:
        """获取验证码统计信息"""
        try:
            code_keys = list(self.redis.keys(
                "verification_code:*"))  # type: ignore
            session_keys = list(self.redis.keys(
                "verification_session:*"))  # type: ignore
            rate_limit_keys = list(self.redis.keys(
                "verification_rate_limit:*"))  # type: ignore

            return {
                "total_codes": len(code_keys),
                "total_sessions": len(session_keys),
                "total_rate_limits": len(rate_limit_keys),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {
                "total_codes": 0,
                "total_sessions": 0,
                "total_rate_limits": 0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            }


# CLI工具
if __name__ == "__main__":
    import sys

    manager = RedisVerificationManager()

    if len(sys.argv) < 2:
        print("用法:")
        print("  python redis_verification_manager.py stats - 显示统计信息")
        print("  python redis_verification_manager.py list-codes - 列出所有验证码")
        print("  python redis_verification_manager.py cleanup - 清理所有验证码数据")
        sys.exit(1)

    command = sys.argv[1]

    if command == "stats":
        stats = manager.get_stats()
        print("Redis验证码统计信息:")
        for key, value in stats.items():
            print(f"  {key}: {value}")

    elif command == "list-codes":
        codes = manager.list_all_verification_codes()
        print(f"找到 {len(codes)} 个验证码:")
        for code in codes:
            print(
                f"  邮箱: {code['email']}, 用途: {code['purpose']}, 尝试次数: {code['attempts']}, TTL: {code['ttl']}s")

    elif command == "cleanup":
        result = manager.cleanup_all_verification_data()
        print(f"清理完成，删除了 {result['deleted_count']} 个键")

    else:
        print(f"未知命令: {command}")
        sys.exit(1)
