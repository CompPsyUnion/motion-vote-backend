"""活动服务模块

处理活动相关的业务逻辑，包括：
- 活动的CRUD操作
- 协作者管理
- 权限验证
- 活动状态管理
"""

from datetime import datetime
from math import ceil
from typing import List, Optional
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, selectinload
from src.models.activity import Activity, Collaborator
from src.models.debate import Debate
from src.models.user import User
from src.models.vote import Participant, Vote
from src.schemas.activity import (ActivityCreate, ActivityDetail,
                                  ActivityDetailStatistics, ActivityResponse,
                                  ActivityStatus, ActivityUpdate,
                                  CollaboratorInvite, CollaboratorPermission,
                                  CollaboratorResponse, CollaboratorStatus,
                                  CollaboratorUpdate, PaginatedActivities)


class ActivityService:
    """活动服务类"""

    def __init__(self, db: Session):
        self.db = db

    def get_activities_paginated(
        self,
        user_id: str,
        page: int = 1,
        limit: int = 20,
        status: Optional[str] = None,
        role: Optional[str] = None,
        search: Optional[str] = None
    ) -> PaginatedActivities:
        """获取分页活动列表"""
        # 处理查询参数
        page = max(1, page)
        limit = max(1, min(100, limit))

        # 处理状态参数
        status_enum = None
        if status and status.strip():
            try:
                status_enum = ActivityStatus(status.strip().lower())
            except ValueError:
                status_enum = None

        query = self.db.query(Activity)

        # 筛选用户相关的活动
        if role and role.lower() == "owner":
            query = query.filter(Activity.owner_id == user_id)
        elif role and role.lower() == "collaborator":
            # 获取用户作为协作者的活动ID
            collaborator_activity_ids = self.db.query(Collaborator.activity_id).filter(
                Collaborator.user_id == user_id,
                Collaborator.status == CollaboratorStatus.accepted
            ).all()
            activity_ids = [str(c.activity_id)
                            for c in collaborator_activity_ids]
            if activity_ids:
                query = query.filter(Activity.id.in_(activity_ids))
            else:
                # 如果没有协作的活动，返回空结果
                query = query.filter(Activity.id.is_(None))
        else:
            # 默认获取用户创建或协作者的活动 - 使用更简单的方法
            owned_activities = query.filter(Activity.owner_id == user_id)

            # 获取协作的活动ID
            collaborator_activity_ids = self.db.query(Collaborator.activity_id).filter(
                Collaborator.user_id == user_id,
                Collaborator.status == CollaboratorStatus.accepted
            ).all()

            if collaborator_activity_ids:
                activity_ids = [str(c.activity_id)
                                for c in collaborator_activity_ids]
                collaborated_activities = self.db.query(
                    Activity).filter(Activity.id.in_(activity_ids))

                # 合并两个查询结果 - 使用Python集合去重
                owned_ids = {str(a.id) for a in owned_activities.all()}
                collab_ids = {str(a.id) for a in collaborated_activities.all()}
                all_activity_ids = list(owned_ids | collab_ids)

                if all_activity_ids:
                    query = query.filter(Activity.id.in_(all_activity_ids))
                else:
                    query = query.filter(Activity.id.is_(None))
            else:
                # 只有拥有的活动
                query = query.filter(Activity.owner_id == user_id)

        # 状态筛选
        if status_enum:
            query = query.filter(Activity.status == status_enum)

        # 搜索 - 支持多关键词模糊匹配
        if search and search.strip():
            search_terms = search.strip().split()
            search_conditions = []

            for term in search_terms:
                term_pattern = f"%{term}%"
                term_conditions = [
                    Activity.name.ilike(term_pattern),
                    Activity.description.ilike(term_pattern),
                    Activity.location.ilike(term_pattern)
                ]

                # 如果Activity有tags字段，也进行搜索
                # 注意：这里暂时不搜索tags，可以在需要时添加更复杂的JSON搜索逻辑

                search_conditions.append(or_(*term_conditions))

            if search_conditions:
                query = query.filter(and_(*search_conditions))

        # 排序：按创建时间倒序
        query = query.order_by(Activity.created_at.desc())

        # 分页
        total = query.count()
        activities = query.offset((page - 1) * limit).limit(limit).all()

        # 转换为响应模式
        activity_responses = [ActivityResponse.model_validate(
            activity) for activity in activities]

        return PaginatedActivities(
            items=activity_responses,
            total=total,
            page=page,
            limit=limit,
            total_pages=ceil(total / limit) if limit > 0 else 0
        )

    def create_activity(self, activity_data: ActivityCreate, owner_id: str) -> ActivityResponse:
        """创建活动"""
        # 使用by_alias=True来获取数据库字段名(snake_case)
        activity_dict = activity_data.model_dump(by_alias=True)

        # 生成UUID
        activity_id = str(uuid4())

        activity = Activity(
            id=activity_id,
            **activity_dict,
            owner_id=owner_id
        )

        self.db.add(activity)
        self.db.commit()
        self.db.refresh(activity)

        return ActivityResponse.model_validate(activity)

    def get_activity_by_id(self, activity_id: str, user_id: str) -> ActivityResponse:
        """根据ID获取活动"""
        activity = self.db.query(Activity).filter(
            Activity.id == activity_id).first()
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")

        # 检查权限：所有者或协作者
        if str(activity.owner_id) != user_id:
            collaborator = self._get_user_collaboration(activity_id, user_id)
            if not collaborator:
                raise HTTPException(
                    status_code=403, detail="Permission denied")

        return ActivityResponse.model_validate(activity)

    def get_activity_detail(self, activity_id: str, user_id: str) -> ActivityDetail:
        """获取活动详情，包含协作者、辩题等信息"""
        # 使用 selectinload 预加载相关数据
        activity = self.db.query(Activity)\
            .options(
                selectinload(Activity.collaborators).selectinload(
                    Collaborator.user),
                selectinload(Activity.debates),
                selectinload(Activity.current_debate),
                selectinload(Activity.owner)
        )\
            .filter(Activity.id == activity_id)\
            .first()

        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")

        # 检查权限
        if str(activity.owner_id) != user_id:
            collaborator = self._get_user_collaboration(activity_id, user_id)
            if not collaborator:
                raise HTTPException(
                    status_code=403, detail="Permission denied")

        # 计算统计信息
        statistics = self._get_activity_statistics(activity_id)

        # 构建响应
        activity_dict = {
            **ActivityResponse.model_validate(activity).model_dump(),
            "collaborators": [self._build_collaborator_response(c) for c in activity.collaborators],
            "debates": [{"id": d.id, "title": d.title, "status": d.status} for d in activity.debates],
            "currentDebate": {"id": activity.current_debate.id, "title": activity.current_debate.title} if activity.current_debate else None,
            "statistics": statistics
        }

        return ActivityDetail(**activity_dict)

    def update_activity(self, activity_id: str, activity_data: ActivityUpdate, user_id: str) -> ActivityResponse:
        """更新活动"""
        activity = self.db.query(Activity).filter(
            Activity.id == activity_id).first()
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")

        # 检查权限：所有者或有edit权限的协作者
        if str(activity.owner_id) != user_id:
            collaborator = self._get_user_collaboration(activity_id, user_id)
            if not collaborator or CollaboratorPermission.edit not in collaborator.permissions:
                raise HTTPException(
                    status_code=403, detail="Permission denied")

        # 更新字段
        update_data = activity_data.model_dump(
            exclude_unset=True, by_alias=True)
        for field, value in update_data.items():
            setattr(activity, field, value)

        self.db.commit()
        self.db.refresh(activity)

        # 如果更新了settings,清除Redis缓存
        if 'settings' in update_data:
            from backend.src.services.vote_service import VoteService
            vote_service = VoteService(self.db)
            vote_service.invalidate_activity_config_cache(activity_id)

        return ActivityResponse.model_validate(activity)

    def delete_activity(self, activity_id: str, user_id: str) -> dict:
        """删除活动"""
        activity = self.db.query(Activity).filter(
            Activity.id == activity_id).first()
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")

        # 只有所有者可以删除
        if str(activity.owner_id) != user_id:
            raise HTTPException(
                status_code=403, detail="Only owner can delete activity")

        self.db.delete(activity)
        self.db.commit()

        return {"success": True, "message": "Activity deleted successfully", "timestamp": datetime.now()}

    def get_collaborators(self, activity_id: str, user_id: str) -> List[CollaboratorResponse]:
        """获取协作者列表"""
        activity = self.db.query(Activity).filter(
            Activity.id == activity_id).first()
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")

        # 检查权限：所有者或协作者
        if str(activity.owner_id) != user_id:
            collaborator = self._get_user_collaboration(activity_id, user_id)
            if not collaborator:
                raise HTTPException(
                    status_code=403, detail="Permission denied")

        collaborators = self.db.query(Collaborator)\
            .options(selectinload(Collaborator.user))\
            .filter(Collaborator.activity_id == activity_id)\
            .all()

        return [self._build_collaborator_response(c) for c in collaborators]

    def invite_collaborator(self, activity_id: str, invite_data: CollaboratorInvite, user_id: str) -> CollaboratorResponse:
        """邀请协作者"""
        activity = self.db.query(Activity).filter(
            Activity.id == activity_id).first()
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")

        # 只有所有者可以邀请协作者
        if str(activity.owner_id) != user_id:
            raise HTTPException(
                status_code=403, detail="Only owner can invite collaborators")

        # 检查用户是否存在
        user = self.db.query(User).filter(
            User.email == invite_data.email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # 检查是否已经是协作者
        existing = self.db.query(Collaborator).filter(
            Collaborator.activity_id == activity_id,
            Collaborator.user_id == user.id
        ).first()
        if existing:
            raise HTTPException(
                status_code=400, detail="User is already a collaborator")

        collaborator = Collaborator(
            id=str(uuid4()),
            user_id=user.id,
            activity_id=activity_id,
            permissions=invite_data.permissions
        )

        self.db.add(collaborator)
        self.db.commit()
        self.db.refresh(collaborator)

        # 重新查询以获取用户信息
        collaborator_with_user = self.db.query(Collaborator)\
            .options(selectinload(Collaborator.user))\
            .filter(Collaborator.id == collaborator.id)\
            .first()

        return self._build_collaborator_response(collaborator_with_user)

    def update_collaborator_permissions(
        self,
        activity_id: str,
        collaborator_id: str,
        update_data: CollaboratorUpdate,
        user_id: str
    ) -> CollaboratorResponse:
        """更新协作者权限"""
        activity = self.db.query(Activity).filter(
            Activity.id == activity_id).first()
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")

        # 只有所有者可以更新权限
        if str(activity.owner_id) != user_id:
            raise HTTPException(
                status_code=403, detail="Only owner can update collaborator permissions")

        collaborator = self.db.query(Collaborator)\
            .options(selectinload(Collaborator.user))\
            .filter(
                Collaborator.id == collaborator_id,
                Collaborator.activity_id == activity_id
        )\
            .first()

        if not collaborator:
            raise HTTPException(
                status_code=404, detail="Collaborator not found")

        setattr(collaborator, 'permissions', update_data.permissions)
        self.db.commit()
        self.db.refresh(collaborator)

        return self._build_collaborator_response(collaborator)

    def remove_collaborator(self, activity_id: str, collaborator_id: str, user_id: str) -> dict:
        """移除协作者"""
        activity = self.db.query(Activity).filter(
            Activity.id == activity_id).first()
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")

        # 只有所有者可以移除协作者
        if str(activity.owner_id) != user_id:
            raise HTTPException(
                status_code=403, detail="Only owner can remove collaborators")

        collaborator = self.db.query(Collaborator).filter(
            Collaborator.id == collaborator_id,
            Collaborator.activity_id == activity_id
        ).first()

        if not collaborator:
            raise HTTPException(
                status_code=404, detail="Collaborator not found")

        self.db.delete(collaborator)
        self.db.commit()

        return {"success": True, "message": "Collaborator removed successfully", "timestamp": datetime.now()}

    def _get_user_collaboration(self, activity_id: str, user_id: str) -> Optional[Collaborator]:
        """获取用户在活动中的协作关系"""
        return self.db.query(Collaborator).filter(
            Collaborator.activity_id == activity_id,
            Collaborator.user_id == user_id,
            Collaborator.status == CollaboratorStatus.accepted
        ).first()

    def _get_activity_statistics(self, activity_id: str) -> ActivityDetailStatistics:
        """获取活动统计信息"""
        # 获取参与者统计
        total_participants = self.db.query(Participant)\
            .filter(Participant.activity_id == activity_id)\
            .count()

        checked_in_participants = self.db.query(Participant)\
            .filter(
                Participant.activity_id == activity_id,
                Participant.checked_in == True
        )\
            .count()

        # 总投票数
        total_votes = self.db.query(Vote)\
            .join(Debate, Vote.debate_id == Debate.id)\
            .filter(Debate.activity_id == activity_id)\
            .count()

        # 辩题总数
        total_debates = self.db.query(Debate)\
            .filter(Debate.activity_id == activity_id)\
            .count()

        return ActivityDetailStatistics(
            total_participants=total_participants,
            checked_in_participants=checked_in_participants,
            total_votes=total_votes,
            total_debates=total_debates
        )

    def _build_collaborator_response(self, collaborator: Collaborator) -> CollaboratorResponse:
        """构建协作者响应"""
        # 直接使用 model_validate 来转换
        collaborator_dict = {
            "id": collaborator.id,
            "user": {
                "id": collaborator.user.id,
                "name": collaborator.user.name,
                "email": collaborator.user.email,
                "avatar": getattr(collaborator.user, 'avatar', None)
            },
            "permissions": collaborator.permissions,
            "status": collaborator.status,
            "invited_at": collaborator.invited_at,
            "accepted_at": collaborator.accepted_at
        }

        return CollaboratorResponse.model_validate(collaborator_dict)

    def check_user_permission(self, activity_id: str, user_id: str, required_permission: CollaboratorPermission) -> bool:
        """检查用户是否具有指定权限"""
        activity = self.db.query(Activity).filter(
            Activity.id == activity_id).first()
        if not activity:
            return False

        # 所有者拥有所有权限
        if str(activity.owner_id) == user_id:
            return True

        # 检查协作者权限
        collaborator = self._get_user_collaboration(activity_id, user_id)
        if not collaborator:
            return False

        return required_permission in collaborator.permissions
