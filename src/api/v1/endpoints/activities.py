"""活动管理 API 端点

基于 OpenAPI 规范实现的活动管理接口，包括：
- 活动的CRUD操作
- 协作者管理
- 权限控制
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user, get_db
from src.models.user import User
from src.schemas.activity import (
    ActivityCreate, ActivityResponse, ActivityDetail, ActivityUpdate,
    CollaboratorInvite, CollaboratorResponse, CollaboratorUpdate,
    PaginatedActivities
)
from src.schemas.base import ApiResponse
from src.services.activity_service import ActivityService

router = APIRouter()


@router.get("/", response_model=PaginatedActivities)
async def get_activities(
    page: int = Query(default=1, description="页码"),
    limit: int = Query(default=20, description="每页数量"),
    status: Optional[str] = Query(default=None, description="活动状态筛选", regex="^(upcoming|ongoing|ended)$"),
    role: Optional[str] = Query(default=None, description="用户角色筛选", regex="^(owner|collaborator)$"),
    search: Optional[str] = Query(default=None, description="搜索关键词"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取用户创建和参与的活动列表"""
    service = ActivityService(db)
    return service.get_activities_paginated(
        user_id=str(current_user.id),
        page=page,
        limit=limit,
        status=status,
        role=role,
        search=search
    )


@router.post("/", response_model=ActivityResponse, status_code=201)
async def create_activity(
    activity_data: ActivityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建新的辩论活动"""
    service = ActivityService(db)
    return service.create_activity(activity_data, str(current_user.id))


@router.get("/{activity_id}", response_model=ActivityDetail)
async def get_activity_detail(
    activity_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取指定活动的详细信息"""
    service = ActivityService(db)
    return service.get_activity_detail(activity_id, str(current_user.id))


@router.put("/{activity_id}", response_model=ApiResponse)
async def update_activity(
    activity_id: str,
    activity_data: ActivityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新活动信息"""
    service = ActivityService(db)
    service.update_activity(activity_id, activity_data, str(current_user.id))
    return ApiResponse(
        message="Activity updated successfully"
    )


@router.delete("/{activity_id}", response_model=ApiResponse)
async def delete_activity(
    activity_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除指定活动"""
    service = ActivityService(db)
    service.delete_activity(activity_id, str(current_user.id))
    return ApiResponse(
        message="Activity deleted successfully"
    )


@router.get("/{activity_id}/collaborators", response_model=List[CollaboratorResponse])
async def get_collaborators(
    activity_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取活动的协作者列表"""
    service = ActivityService(db)
    return service.get_collaborators(activity_id, str(current_user.id))


@router.post("/{activity_id}/collaborators", response_model=ApiResponse, status_code=201)
async def invite_collaborator(
    activity_id: str,
    invite_data: CollaboratorInvite,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """邀请用户成为活动协作者"""
    service = ActivityService(db)
    service.invite_collaborator(activity_id, invite_data, str(current_user.id))
    return ApiResponse(
        message="Collaborator invited successfully"
    )


@router.put("/{activity_id}/collaborators/{collaborator_id}", response_model=ApiResponse)
async def update_collaborator_permissions(
    activity_id: str,
    collaborator_id: str,
    update_data: CollaboratorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新协作者的权限设置"""
    service = ActivityService(db)
    service.update_collaborator_permissions(
        activity_id, collaborator_id, update_data, str(current_user.id)
    )
    return ApiResponse(
        message="Collaborator permissions updated successfully"
    )


@router.delete("/{activity_id}/collaborators/{collaborator_id}", response_model=ApiResponse)
async def remove_collaborator(
    activity_id: str,
    collaborator_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """从活动中移除协作者"""
    service = ActivityService(db)
    service.remove_collaborator(activity_id, collaborator_id, str(current_user.id))
    return ApiResponse(
        message="Collaborator removed successfully"
    )
