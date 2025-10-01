"""独立的参与者资源 API 端点

处理不依赖于活动ID的参与者相关端点
"""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user, get_db
from src.models.user import User
from src.schemas.participant import ParticipantEnter, ParticipantLinksResponse
from src.services.participant_service import ParticipantService

router = APIRouter()


@router.get("/participants/{participant_id}/link", response_model=dict)
async def generate_participant_link(
    participant_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取参与者链接参数
    
    返回参与者的活动ID和编号，用于前端构建链接
    """
    service = ParticipantService(db)
    links_data = service.generate_participant_link(
        participant_id=participant_id,
        user_id=str(current_user.id)
    )
    
    return {
        "success": True,
        "message": "链接生成成功",
        "data": links_data
    }


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


# votes/enter端点已移动到votes.py文件中