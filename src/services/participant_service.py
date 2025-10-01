from typing import Optional
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import and_
from sqlalchemy.orm import Session

from src.models.activity import Activity
from src.models.vote import Participant
from src.schemas.participant import (
    ParticipantCreate, ParticipantResponse,
    PaginatedParticipants, ParticipantBatchImportResult
)


class ParticipantService:
    def __init__(self, db: Session):
        self.db = db

    def _check_activity_permission(self, activity_id: str, user_id: str) -> Activity:
        """检查用户对活动的权限"""
        activity = self.db.query(Activity).filter(Activity.id == activity_id).first()
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")
        
        # 检查是否是活动拥有者或协作者（简化检查）
        if str(activity.owner_id) != str(user_id):
            # TODO: 检查是否是协作者
            pass
        
        return activity

    def get_participants_paginated(
        self,
        activity_id: str,
        user_id: str,
        page: int = 1,
        limit: int = 50,
        status: Optional[str] = None
    ) -> PaginatedParticipants:
        """获取分页参与者列表"""
        # 检查权限
        self._check_activity_permission(activity_id, user_id)
        
        # 构建查询
        query = self.db.query(Participant).filter(Participant.activity_id == activity_id)
        
        # 状态筛选
        if status == "checked_in":
            query = query.filter(Participant.checked_in == True)
        elif status == "not_checked_in":
            query = query.filter(Participant.checked_in == False)
        
        # 计算总数
        total = query.count()
        
        # 分页
        offset = (page - 1) * limit
        participants = query.offset(offset).limit(limit).all()
        
        # 计算总页数
        total_pages = (total + limit - 1) // limit
        
        return PaginatedParticipants(
            items=[ParticipantResponse.model_validate(p) for p in participants],
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages
        )

    def create_participant(
        self,
        activity_id: str,
        participant_data: ParticipantCreate,
        user_id: str
    ) -> ParticipantResponse:
        """创建参与者"""
        # 检查权限
        self._check_activity_permission(activity_id, user_id)
        
        # 生成参与者编号
        code = self._generate_participant_code(activity_id)
        
        # 创建参与者
        participant = Participant(
            activity_id=activity_id,
            code=code,
            name=participant_data.name,
            phone=participant_data.phone,
            note=participant_data.note
        )
        
        self.db.add(participant)
        self.db.commit()
        self.db.refresh(participant)
        
        return ParticipantResponse.model_validate(participant)

    def _generate_participant_code(self, activity_id: str) -> str:
        """生成参与者编号"""
        # 获取当前活动的参与者数量
        count = self.db.query(Participant).filter(
            Participant.activity_id == activity_id
        ).count()
        return f"{count + 1:04d}"  # 生成4位数字编号，如0001, 0002

    def batch_import_participants(
        self,
        activity_id: str,
        file,
        user_id: str
    ) -> ParticipantBatchImportResult:
        """批量导入参与者（简化版本）"""
        # 检查权限
        self._check_activity_permission(activity_id, user_id)
        
        # 简化实现，返回基本结果
        return ParticipantBatchImportResult(
            total=0,
            success=0,
            failed=0,
            errors=["批量导入功能待实现"]
        )

    def export_participants(self, activity_id: str, user_id: str) -> bytes:
        """导出参与者数据为Excel（简化版本）"""
        # 检查权限
        self._check_activity_permission(activity_id, user_id)
        
        # 简化实现，返回空字节
        return b"Export functionality not implemented yet"

    def generate_participant_link(self, participant_id: str, user_id: str) -> str:
        """生成参与者投票链接"""
        participant = self.db.query(Participant).filter(Participant.id == participant_id).first()
        if not participant:
            raise HTTPException(status_code=404, detail="Participant not found")
        
        # 检查权限
        self._check_activity_permission(str(participant.activity_id), user_id)
        
        # 生成链接
        base_url = "http://localhost:3000"  # 这应该从配置中获取
        return f"{base_url}/vote?activityId={participant.activity_id}&code={participant.code}"

    def generate_participant_qrcode(self, participant_id: str, user_id: str) -> bytes:
        """生成参与者二维码（简化版本）"""
        # 简化实现，返回空字节
        return b"QR code generation not implemented yet"

    def participant_enter(
        self,
        activity_id: str,
        participant_code: str,
        device_fingerprint: Optional[str] = None
    ) -> tuple[dict, dict]:
        """参与者入场"""
        # 查找参与者
        participant = self.db.query(Participant).filter(
            and_(
                Participant.activity_id == activity_id,
                Participant.code == participant_code
            )
        ).first()
        
        if not participant:
            raise HTTPException(status_code=404, detail="参与者不存在或编号错误")
        
        # 更新入场状态（简化实现）
        # 注意：这里不直接修改SQLAlchemy对象的属性，而是使用update方法
        self.db.query(Participant).filter(Participant.id == participant.id).update({
            "checked_in": True,
            "checked_in_at": datetime.utcnow(),
            "device_fingerprint": device_fingerprint
        })
        self.db.commit()
        
        # 获取活动信息
        activity = self.db.query(Activity).filter(Activity.id == activity_id).first()
        
        activity_info = {
            "activity": {
                "id": str(activity.id) if activity else "",
                "name": str(activity.name) if activity else "",
                "status": activity.status.value if activity else "unknown",
                "current_debate": None  # TODO: 获取当前辩题
            },
            "participant": {
                "id": str(participant.id),
                "code": str(participant.code),
                "name": str(participant.name)
            }
        }
        
        vote_status = {
            "has_voted": False,  # TODO: 检查投票状态
            "position": None,
            "voted_at": None,
            "remaining_changes": 3,  # TODO: 从设置中获取
            "can_vote": True,
            "can_change": True
        }
        
        return activity_info, vote_status