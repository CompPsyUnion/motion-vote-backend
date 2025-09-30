from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, text, select, union_all
from typing import List, Optional
from math import ceil
from src.api.dependencies import get_db, get_current_user
from src.models.activity import Activity, Collaborator
from src.models.user import User
from src.schemas.activity import (
    ActivityResponse, ActivityCreate, ActivityUpdate,
    PaginatedActivities, CollaboratorResponse, CollaboratorInvite, CollaboratorUpdate,
    ActivityStatus, CollaboratorStatus
)

router = APIRouter()


@router.get("/activities", response_model=PaginatedActivities)
async def get_activities(
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[ActivityStatus] = Query(None, description="活动状态筛选"),
    role: Optional[str] = Query(
        None, description="用户角色筛选", regex="^(owner|collaborator)$"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取活动列表"""
    query = db.query(Activity)

    # 筛选用户相关的活动
    if role == "owner":
        query = query.filter(Activity.owner_id == str(current_user.id))
    elif role == "collaborator":
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
    if status:
        query = query.filter(Activity.status == status)

    # 搜索
    if search:
        query = query.filter(
            or_(
                Activity.name.ilike(f"%{search}%"),
                Activity.description.ilike(f"%{search}%"),
                Activity.location.ilike(f"%{search}%")
            )
        )

    # 分页
    total = query.count()
    activities = query.offset((page - 1) * limit).limit(limit).all()
    # Convert ORM objects to schema objects
    activity_responses = [ActivityResponse.model_validate(
        activity) for activity in activities]

    return PaginatedActivities(
        items=activity_responses,
        total=total,
        page=page,
        limit=limit,
        pages=ceil(total / limit)
    )


@router.post("/activities", response_model=ActivityResponse)
async def create_activity(
    activity_data: ActivityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建活动"""
    activity = Activity(
        **activity_data.model_dump(),
        owner_id=str(current_user.id)
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity


@router.get("/activities/{activity_id}", response_model=ActivityResponse)
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


@router.put("/activities/{activity_id}", response_model=ActivityResponse)
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

    # 更新字段
    update_data = activity_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(activity, field, value)

    db.commit()
    db.refresh(activity)
    return activity


@router.delete("/activities/{activity_id}")
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


@router.get("/activities/{activity_id}/collaborators", response_model=List[CollaboratorResponse])
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


@router.post("/activities/{activity_id}/collaborators", response_model=CollaboratorResponse)
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


@router.put("/activities/{activity_id}/collaborators/{collaborator_id}", response_model=CollaboratorResponse)
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


@router.delete("/activities/{activity_id}/collaborators/{collaborator_id}")
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
