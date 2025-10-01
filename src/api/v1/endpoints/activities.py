from math import ceil
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, or_, select, text, union_all
from sqlalchemy.orm import Session
from src.api.dependencies import get_current_user, get_db
from src.models.activity import Activity, Collaborator
from src.models.user import User
from src.schemas.activity import (ActivityCreate, ActivityResponse,
                                  ActivityStatus, ActivityUpdate,
                                  CollaboratorInvite, CollaboratorResponse,
                                  CollaboratorStatus, CollaboratorUpdate,
                                  PaginatedActivities)

router = APIRouter()


@router.get("/", response_model=PaginatedActivities)
async def get_activities(
    page: Optional[str] = Query(default=None, description="页码"),
    limit: Optional[str] = Query(default=None, description="每页数量"),
    status: Optional[str] = Query(default=None, description="活动状态筛选"),
    role: Optional[str] = Query(default=None, description="用户角色筛选"),
    search: Optional[str] = Query(default=None, description="搜索关键词"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取活动列表"""
    # 处理查询参数，提供默认值和类型转换
    try:
        page_int = int(page) if page and page.strip() else 1
        page_int = max(1, page_int)  # 确保页码至少为1
    except (ValueError, TypeError):
        page_int = 1
    
    try:
        limit_int = int(limit) if limit and limit.strip() else 20
        limit_int = max(1, min(100, limit_int))  # 限制在1-100之间
    except (ValueError, TypeError):
        limit_int = 20
    
    # 处理状态参数
    status_enum = None
    if status and status.strip():
        try:
            status_enum = ActivityStatus(status.strip().lower())
        except ValueError:
            status_enum = None
    
    query = db.query(Activity)

    # 筛选用户相关的活动
    if role and role.lower() == "owner":
        query = query.filter(Activity.owner_id == str(current_user.id))
    elif role and role.lower() == "collaborator":
        # 获取用户作为协作者的活动ID
        collaborator_activity_ids = db.query(Collaborator.activity_id).filter(
            Collaborator.user_id == str(current_user.id),
            Collaborator.status == CollaboratorStatus.accepted
        ).subquery()
        # 使用 select() 取出子查询的列，确保类型兼容
        query = query.filter(Activity.id.in_(
            select(collaborator_activity_ids.c.activity_id)))
    else:
        # 默认获取用户创建或协作者的活动
        all_ids = union_all(
            select(Activity.id.label('activity_id')).where(
                Activity.owner_id == str(current_user.id)),
            select(Collaborator.activity_id.label('activity_id')).where(
                Collaborator.user_id == str(current_user.id),
                Collaborator.status == CollaboratorStatus.accepted
            )
        ).subquery()
        query = query.filter(Activity.id.in_(select(all_ids.c.activity_id)))

    # 状态筛选
    if status_enum:
        query = query.filter(Activity.status == status_enum)

    # 搜索 - 支持多关键词模糊匹配
    if search and search.strip():
        search_terms = search.strip().split()
        search_conditions = []
        
        for term in search_terms:
            term_pattern = f"%{term}%"
            search_conditions.append(
                or_(
                    Activity.name.ilike(term_pattern),
                    Activity.description.ilike(term_pattern),
                    Activity.location.ilike(term_pattern)
                )
            )
        
        # 所有搜索词都要匹配（AND 逻辑）
        if search_conditions:
            query = query.filter(and_(*search_conditions))

    # 排序：按创建时间倒序
    query = query.order_by(Activity.created_at.desc())
    
    # 分页
    total = query.count()
    activities = query.offset((page_int - 1) * limit_int).limit(limit_int).all()
    # Convert ORM objects to schema objects
    activity_responses = [ActivityResponse.model_validate(
        activity) for activity in activities]

    return PaginatedActivities(
        items=activity_responses,
        total=total,
        page=page_int,
        limit=limit_int,
        pages=ceil(total / limit_int) if limit_int > 0 else 0
    )


@router.post("/", response_model=ActivityResponse)
async def create_activity(
    activity_data: ActivityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建活动"""
    # 使用by_alias=True来获取数据库字段名(snake_case)
    activity_dict = activity_data.model_dump(by_alias=True)
    activity = Activity(
        **activity_dict,
        owner_id=str(current_user.id)
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity


@router.get("/{activity_id}", response_model=ActivityResponse)
async def get_activity(
    activity_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取活动详情"""
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # 检查权限：所有者或协作者
    if str(activity.owner_id) != str(current_user.id):
        collaborator = db.query(Collaborator).filter(
            Collaborator.activity_id == activity_id,
            Collaborator.user_id == current_user.id,
            Collaborator.status == CollaboratorStatus.accepted
        ).first()
        if not collaborator:
            raise HTTPException(status_code=403, detail="Permission denied")

    return activity


@router.put("/{activity_id}", response_model=ActivityResponse)
async def update_activity(
    activity_id: str,
    activity_data: ActivityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新活动"""
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # 检查权限：所有者或有edit权限的协作者
    if str(activity.owner_id) != str(current_user.id):
        collaborator = db.query(Collaborator).filter(
            Collaborator.activity_id == activity_id,
            Collaborator.user_id == current_user.id,
            Collaborator.status == CollaboratorStatus.accepted,
            text("JSON_CONTAINS(permissions, '\"edit\"') = 1")
        ).first()
        if not collaborator:
            raise HTTPException(status_code=403, detail="Permission denied")

    # 更新字段 - 使用by_alias=True来获取数据库字段名(snake_case)
    update_data = activity_data.model_dump(exclude_unset=True, by_alias=True)
    for field, value in update_data.items():
        setattr(activity, field, value)

    db.commit()
    db.refresh(activity)
    return activity


@router.delete("/{activity_id}")
async def delete_activity(
    activity_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除活动"""
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # 只有所有者可以删除
    if str(activity.owner_id) != str(current_user.id):
        raise HTTPException(
            status_code=403, detail="Only owner can delete activity")

    db.delete(activity)
    db.commit()
    return {"message": "Activity deleted successfully"}


@router.get("/{activity_id}/collaborators", response_model=List[CollaboratorResponse])
async def get_collaborators(
    activity_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取协作者列表"""
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # 检查权限：所有者或协作者
    if str(activity.owner_id) != str(current_user.id):
        collaborator = db.query(Collaborator).filter(
            Collaborator.activity_id == activity_id,
            Collaborator.user_id == current_user.id,
            Collaborator.status == CollaboratorStatus.accepted
        ).first()
        if not collaborator:
            raise HTTPException(status_code=403, detail="Permission denied")

    collaborators = db.query(Collaborator).filter(
        Collaborator.activity_id == activity_id).all()
    return collaborators


@router.post("/{activity_id}/collaborators", response_model=CollaboratorResponse)
async def invite_collaborator(
    activity_id: str,
    invite_data: CollaboratorInvite,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """邀请协作者"""
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # 只有所有者可以邀请协作者
    if str(activity.owner_id) != str(current_user.id):
        raise HTTPException(
            status_code=403, detail="Only owner can invite collaborators")

    # 检查用户是否存在
    user = db.query(User).filter(User.email == invite_data.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 检查是否已经是协作者
    existing = db.query(Collaborator).filter(
        Collaborator.activity_id == activity_id,
        Collaborator.user_id == user.id
    ).first()
    if existing:
        raise HTTPException(
            status_code=400, detail="User is already a collaborator")

    collaborator = Collaborator(
        user_id=user.id,
        activity_id=activity_id,
        permissions=invite_data.permissions
    )
    db.add(collaborator)
    db.commit()
    db.refresh(collaborator)
    return collaborator


@router.put("/{activity_id}/collaborators/{collaborator_id}", response_model=CollaboratorResponse)
async def update_collaborator(
    activity_id: str,
    collaborator_id: str,
    update_data: CollaboratorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新协作者权限"""
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # 只有所有者可以更新权限
    if str(activity.owner_id) != str(current_user.id):
        raise HTTPException(
            status_code=403, detail="Only owner can update collaborator permissions")

    collaborator = db.query(Collaborator).filter(
        Collaborator.id == collaborator_id,
        Collaborator.activity_id == activity_id
    ).first()
    if not collaborator:
        raise HTTPException(status_code=404, detail="Collaborator not found")

    setattr(collaborator, 'permissions', update_data.permissions)
    db.commit()
    db.refresh(collaborator)
    return collaborator


@router.delete("/{activity_id}/collaborators/{collaborator_id}")
async def remove_collaborator(
    activity_id: str,
    collaborator_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """移除协作者"""
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # 只有所有者可以移除协作者
    if str(activity.owner_id) != str(current_user.id):
        raise HTTPException(
            status_code=403, detail="Only owner can remove collaborators")

    collaborator = db.query(Collaborator).filter(
        Collaborator.id == collaborator_id,
        Collaborator.activity_id == activity_id
    ).first()
    if not collaborator:
        raise HTTPException(status_code=404, detail="Collaborator not found")

    db.delete(collaborator)
    db.commit()
    return {"message": "Collaborator removed successfully"}
