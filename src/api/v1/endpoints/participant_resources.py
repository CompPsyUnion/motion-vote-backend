"""独立的参与者资源 API 端点

处理不依赖于活动ID的参与者相关端点
"""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user, get_db
from src.models.user import User
from src.schemas.participant import ParticipantEnter
from src.services.participant_service import ParticipantService

router = APIRouter()


@router.get("/participants/{participant_id}/link")
async def generate_participant_link(
    participant_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """生成参与者的投票链接"""
    service = ParticipantService(db)
    link = service.generate_participant_link(
        participant_id=participant_id,
        user_id=str(current_user.id)
    )
    
    return Response(content=link, media_type="text/plain")


@router.get("/participants/{participant_id}/qrcode")
async def generate_participant_qrcode(
    participant_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """生成参与者的入场二维码"""
    service = ParticipantService(db)
    qrcode_data = service.generate_participant_qrcode(
        participant_id=participant_id,
        user_id=str(current_user.id)
    )
    
    return Response(content=qrcode_data, media_type="image/png")


@router.post("/votes/enter")
async def participant_enter(
    enter_data: ParticipantEnter,
    db: Session = Depends(get_db)
):
    """参与者通过活动ID和编号进入活动"""
    service = ParticipantService(db)
    activity_info, vote_status = service.participant_enter(
        activity_id=enter_data.activity_id,
        participant_code=enter_data.participant_code,
        device_fingerprint=enter_data.device_fingerprint
    )
    
    return {
        "success": True,
        "message": "入场成功",
        "data": {
            "activity": activity_info["activity"],
            "participant": activity_info["participant"],
            "voteStatus": vote_status
        }
    }