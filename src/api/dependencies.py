from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from src.core.auth import verify_token
from src.core.database import get_db
from src.core.exceptions import AuthenticationError
from src.models.user import User

security = HTTPBearer()


async def get_current_user(
    token=Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """获取当前用户"""
    # 从token中提取用户ID
    payload = verify_token(token.credentials)
    if not payload:
        raise AuthenticationError("Invalid token")

    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationError("Invalid token payload")

    # 从数据库获取用户
    user = db.query(User).filter(User.id == user_id,
                                 User.is_active.is_(True)).first()
    if not user:
        raise AuthenticationError("User not found")

    return user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """获取当前管理员用户"""
    if str(current_user.role) != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user
