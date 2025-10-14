from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session
from src.core.exceptions import NotFoundError
from src.models.user import User
from src.schemas.base import PaginatedResponse
from src.schemas.user import UserResponse, UserRole, UserUpdate


class UserService:
    def __init__(self, db: Session):
        self.db = db

    async def update_user(self, user_id: str, user_update: UserUpdate, current_user_role: UserRole) -> User:
        """更新用户信息"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise NotFoundError("用户不存在")

        # 更新用户信息
        update_data = user_update.dict(exclude_unset=True)

        # 如果更新数据中包含 role，检查权限
        if 'role' in update_data:
            # 只有管理员可以修改角色
            if current_user_role != UserRole.admin:
                raise HTTPException(status_code=403, detail="没有权限修改用户角色")

        for key, value in update_data.items():
            setattr(user, key, value)

        self.db.commit()
        self.db.refresh(user)

        return user

    async def get_users(self, page: int, limit: int, search: Optional[str] = None) -> PaginatedResponse:
        """获取用户列表"""
        query = self.db.query(User)

        # 搜索过滤
        if search:
            query = query.filter(
                User.name.contains(search) | User.email.contains(search)
            )

        # 计算总数
        total = query.count()

        # 分页
        offset = (page - 1) * limit
        users = query.offset(offset).limit(limit).all()

        return PaginatedResponse(
            items=[UserResponse.model_validate(
                user).model_dump() for user in users],
            total=total,
            page=page,
            limit=limit,
            totalPages=(total + limit - 1) // limit
        )
