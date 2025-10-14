from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from src.api.dependencies import get_current_user
from src.core.database import get_db
from src.models.user import User
from src.schemas.base import ApiResponse, PaginatedResponse
from src.schemas.user import UserResponse, UserRole, UserUpdate
from src.services.user_service import UserService

router = APIRouter()


@router.get("/profile", response_model=UserResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户信息"""
    try:
        return UserResponse.model_validate(current_user)
    except Exception as e:
        # 如果验证失败，创建字典并转换
        user_dict = {
            "id": str(current_user.id),
            "email": current_user.email,
            "name": current_user.name,
            "phone": current_user.phone,
            "avatar": current_user.avatar,
            "role": current_user.role,
            "created_at": current_user.created_at,
            "updated_at": current_user.updated_at
        }
        return UserResponse(**user_dict)


@router.put("/profile", response_model=ApiResponse)
async def update_profile(
    user_update: UserUpdate,
    id: Optional[str] = Query(None, description="要更新的用户ID（仅管理员可用）"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新用户信息"""
    user_service = UserService(db)

    # 获取当前用户角色（转换为字符串进行比较）
    current_role_str = str(current_user.role)
    is_admin = current_role_str == "UserRole.admin"

    # 如果指定了 id 参数
    if id is not None:
        # 检查当前用户是否为管理员
        if not is_admin:
            raise HTTPException(status_code=403, detail="只有管理员可以更新其他用户信息")

        # 管理员更新指定用户
        await user_service.update_user(id, user_update, current_user_role=UserRole.admin)
        return ApiResponse(message="用户信息更新成功")
    else:
        # 普通用户更新自己的信息
        # 如果普通用户尝试修改 role，返回权限错误
        if user_update.role is not None and not is_admin:
            raise HTTPException(status_code=403, detail="没有权限修改用户角色")

        # 转换角色
        user_role = UserRole.admin if is_admin else UserRole.organizer
        await user_service.update_user(str(current_user.id), user_update, current_user_role=user_role)
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

    # 获取当前用户角色（转换为字符串进行比较）
    current_role_str = str(current_user.role)
    is_admin = current_role_str == "UserRole.admin"

    if not is_admin:
        raise HTTPException(status_code=403, detail="只有管理员可以获取用户列表")

    return await user_service.get_users(page, limit, search)
