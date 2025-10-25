"""投票系统 API 端点

混合存储方案：
- Redis：实时投票，毫秒级响应
- 数据库：每2秒自动同步持久化
- 接口保持不变，对前端透明
"""


from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from src.api.dependencies import get_db
from src.schemas.vote import ParticipantEnter, VoteRequest
from src.services.vote_service import VoteService

router = APIRouter()


@router.post("/enter")
@router.post("/enter/")
async def participant_enter(
    enter_data: ParticipantEnter,
    db: Session = Depends(get_db)
):
    """参与者入场
    
    支持三种入场方式：
    1. 提供 activity_id 和 participant_code
    2. 直接提供 participant_id（UUID）
    3. 直接提供 participant_id（编号 code）
    """
    from src.models.vote import Participant
    from fastapi import HTTPException
    
    activity_id = enter_data.activity_id
    participant_code = enter_data.participant_code
    participant_id = enter_data.participant_id
    
    # 如果提供了 participant_id，自动查找 activity_id 和 participant_code
    if participant_id:
        # 先尝试按 code 查找（因为二维码中使用的是 code）
        participant = db.query(Participant).filter(Participant.code == participant_id).first()
        
        # 如果按 code 找不到，再尝试按 id 查找（UUID）
        if not participant:
            participant = db.query(Participant).filter(Participant.id == participant_id).first()
        
        if not participant:
            raise HTTPException(status_code=404, detail="参与者不存在")
        
        activity_id = str(participant.activity_id)
        participant_code = participant.code
    elif not (activity_id and participant_code):
        raise HTTPException(status_code=400, detail="缺少必要的参数：需要提供 participant_id 或者 activity_id 和 participant_code")
    
    service = VoteService(db)
    result = service.participant_enter(
        activity_id=activity_id,
        participant_code=participant_code,
        device_fingerprint=enter_data.device_fingerprint
    )

    return {
        "success": True,
        "message": "入场成功",
        "data": result
    }


@router.post("/enter-by-id")
@router.post("/enter-by-id/")
async def participant_enter_by_id(
    request_data: dict,
    db: Session = Depends(get_db)
):
    """参与者通过 participantID 直接进入活动（不需要认证）
    
    支持两种方式：
    1. participantID = participant.id (UUID)
    2. participantID = participant.code (编号，如 0001)
    """
    from src.models.vote import Participant
    from fastapi import HTTPException
    
    participant_id = request_data.get('participant_id') or request_data.get('participantId')
    device_fingerprint = request_data.get('device_fingerprint') or request_data.get('deviceFingerprint')
    
    if not participant_id:
        raise HTTPException(status_code=400, detail="缺少 participant_id 参数")
    
    # 先尝试按 code 查找（因为二维码中使用的是 code）
    participant = db.query(Participant).filter(Participant.code == participant_id).first()
    
    # 如果按 code 找不到，再尝试按 id 查找（UUID）
    if not participant:
        participant = db.query(Participant).filter(Participant.id == participant_id).first()
    
    if not participant:
        raise HTTPException(status_code=404, detail="参与者不存在")
    
    # 调用原有的入场逻辑
    service = VoteService(db)
    result = service.participant_enter(
        activity_id=str(participant.activity_id),
        participant_code=participant.code,
        device_fingerprint=device_fingerprint
    )

    return {
        "success": True,
        "message": "入场成功",
        "data": result
    }


@router.post("/debates/{debate_id}")
@router.post("/debates/{debate_id}/")
async def vote_for_debate(
    debate_id: str,
    vote_data: VoteRequest,
    db: Session = Depends(get_db)
):
    """参与者对指定辩题进行投票（Redis存储 + 2秒同步数据库）"""
    service = VoteService(db)
    result = service.vote_for_debate(
        debate_id=debate_id,
        session_token=vote_data.session_token,
        position=vote_data.position
    )

    return {
        "success": True,
        "message": "投票成功",
        "data": result
    }


@router.get("/debates/{debate_id}")
@router.get("/debates/{debate_id}/")
async def get_vote_status(
    debate_id: str,
    session_token: str = Query(..., alias="sessionToken", description="会话令牌"),
    db: Session = Depends(get_db)
):
    """获取参与者在指定辩题的投票状态（从Redis读取）"""
    service = VoteService(db)
    status = service.get_vote_status(
        debate_id=debate_id,
        session_token=session_token
    )

    return {
        "success": True,
        "message": "获取投票状态成功",
        "data": status
    }


@router.get("/debates/{debate_id}/results")
@router.get("/debates/{debate_id}/results/")
async def get_debate_results(
    debate_id: str,
    db: Session = Depends(get_db)
):
    """获取指定辩题的投票统计结果（从Redis实时计算）"""
    service = VoteService(db)
    results = service.get_debate_results(debate_id=debate_id)

    return {
        "success": True,
        "message": "获取投票结果成功",
        "data": results
    }


@router.delete("/debates/{debate_id}/votes")
async def clear_debate_votes(
    debate_id: str,
    db: Session = Depends(get_db)
):
    """清空指定辩题的所有投票数据（管理员功能）"""
    service = VoteService(db)
    result = service.clear_debate_votes(debate_id=debate_id)

    return {
        "success": True,
        "message": result["message"],
        "data": {
            "deleted_count": result["deleted_count"]
        }
    }
