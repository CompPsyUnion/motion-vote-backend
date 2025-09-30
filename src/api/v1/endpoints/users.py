from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from src.core.database import get_db
from src.schemas.user import UserResponse, UserUpdate
from src.schemas.base import ApiResponse, PaginatedResponse
from src.services.user_service import UserService
from src.api.dependencies import get_current_user
from src.models.user import User

router = APIRouter()


@router.get("/profile", response_model=UserResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户信息"""
    return current_user


@router.put("/profile", response_model=ApiResponse)
async def update_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新用户信息"""
    user_service = UserService(db)
    await user_service.update_user(str(current_user.id), user_update)
    return ApiResponse(message="用户信息更新成功")


@router.get("", response_model=PaginatedResponse)
async def get_users(
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户列表（仅管理员）"""
    user_service = UserService(db)
    return await user_service.get_users(page, limit, search)
