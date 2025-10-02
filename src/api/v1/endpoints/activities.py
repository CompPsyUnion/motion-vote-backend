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
from src.schemas.activity import (ActivityCreate, ActivityDetail,
                                  ActivityResponse, ActivityUpdate,
                                  CollaboratorInvite, CollaboratorResponse,
                                  CollaboratorUpdate, PaginatedActivities)
from src.schemas.base import ApiResponse
from src.services.activity_service import ActivityService

router = APIRouter()


@router.get("/", response_model=PaginatedActivities)
async def get_activities(
    page: int = Query(default=1, ge=1, description="页码"),
    limit: int = Query(default=20, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(
        default=None, description="活动状态筛选 (upcoming|ongoing|ended)"),
    role: Optional[str] = Query(
        default=None, description="用户角色筛选 (owner|collaborator)"),
    search: Optional[str] = Query(
        default=None, description="搜索关键词 - 支持活动名称、描述、地址模糊匹配"),
    name: Optional[str] = Query(default=None, description="活动名称模糊匹配"),
    location: Optional[str] = Query(default=None, description="活动地址模糊匹配"),
    tags: Optional[str] = Query(default=None, description="标签搜索，多个标签用逗号分隔"),
    date_from: Optional[str] = Query(
        default=None, description="开始时间筛选 (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(
        default=None, description="结束时间筛选 (YYYY-MM-DD)"),
    sort_by: Optional[str] = Query(
        default="created_at", description="排序字段 (created_at|name|start_time)"),
    sort_order: Optional[str] = Query(
        default="desc", description="排序方向 (asc|desc)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取用户创建和参与的活动列表

    支持多种筛选和搜索方式：
    - search: 全文搜索(名称、描述、地址)
    - name: 活动名称模糊匹配
    - location: 地址模糊匹配
    - tags: 标签搜索
    - date_from/date_to: 时间范围筛选
    - sort_by/sort_order: 自定义排序
    """
    service = ActivityService(db)
    # 构建增强的搜索参数
    enhanced_search = search
    if name or location or tags:
        search_parts = []
        if enhanced_search:
            search_parts.append(enhanced_search)
        if name:
            search_parts.append(name)
        if location:
            search_parts.append(location)
        if tags:
            search_parts.extend(tags.split(','))
        enhanced_search = ' '.join(search_parts)

    return service.get_activities_paginated(
        user_id=str(current_user.id),
        page=page,
        limit=limit,
        status=status,
        role=role,
        search=enhanced_search
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
    service.remove_collaborator(
        activity_id, collaborator_id, str(current_user.id))
    return ApiResponse(
        message="Collaborator removed successfully"
    )
