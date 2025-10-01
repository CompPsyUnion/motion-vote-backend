from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from src.api.dependencies import get_current_user, get_db
from src.models.activity import Activity, Collaborator
from src.models.debate import Debate
from src.models.user import User
from src.models.vote import Vote
from src.schemas.activity import CollaboratorStatus
from src.schemas.debate import (CurrentDebateUpdate, DebateCreate,
                                DebateDetailResponse, DebateReorder,
                                DebateResponse, DebateStatusUpdate,
                                DebateUpdate, VoteStats)
from src.schemas.vote import VotePosition

router = APIRouter()


def check_activity_permission(
    activity_id: str,
    user_id: str,
    required_permission: str,
    db: Session
) -> Activity:
    """检查活动权限"""
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # 检查是否为所有者
    if str(activity.owner_id) == str(user_id):
        return activity

    # 检查协作者权限
    collaborator = db.query(Collaborator).filter(
        Collaborator.activity_id == activity_id,
        Collaborator.user_id == user_id,
        Collaborator.status == CollaboratorStatus.accepted
    ).first()

    if not collaborator:
        raise HTTPException(status_code=403, detail="Permission denied")

    # 检查具体权限
    if required_permission == "view":
        # view权限所有协作者都有
        return activity
    elif required_permission in ["edit", "control"]:
        # 检查是否有相应权限
        if required_permission not in collaborator.permissions:
            raise HTTPException(
                status_code=403, detail="Insufficient permissions")

    return activity


def get_debate_vote_stats(debate_id: str, db: Session) -> VoteStats:
    """获取辩题投票统计"""
    # 统计各种投票数量
    vote_counts = db.query(
        func.count(Vote.id).label('total_votes'),
        func.sum(func.case([(Vote.position == VotePosition.pro, 1)], else_=0)).label(
            'pro_votes'),
        func.sum(func.case([(Vote.position == VotePosition.con, 1)], else_=0)).label(
            'con_votes'),
        func.sum(func.case([(Vote.position == VotePosition.abstain, 1)], else_=0)).label(
            'abstain_votes')
    ).filter(Vote.debate_id == debate_id).first()

    if vote_counts:
        total_votes = vote_counts.total_votes or 0
        pro_votes = vote_counts.pro_votes or 0
        con_votes = vote_counts.con_votes or 0
        abstain_votes = vote_counts.abstain_votes or 0
    else:
        return VoteStats(
            total_votes=0,
            pro_votes=0,
            con_votes=0,
            abstain_votes=0,
            pro_percentage=0,
            con_percentage=0,
            abstain_percentage=0
        )

    # 计算百分比
    pro_percentage = (pro_votes / total_votes * 100) if total_votes > 0 else 0
    con_percentage = (con_votes / total_votes * 100) if total_votes > 0 else 0
    abstain_percentage = (abstain_votes / total_votes *
                          100) if total_votes > 0 else 0

    return VoteStats(
        total_votes=total_votes,
        pro_votes=pro_votes,
        con_votes=con_votes,
        abstain_votes=abstain_votes,
        pro_percentage=round(pro_percentage, 2),
        con_percentage=round(con_percentage, 2),
        abstain_percentage=round(abstain_percentage, 2)
    )


@router.get("/activities/{activity_id}/debates")
async def get_debates(
    activity_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取辩题列表"""
    # 检查权限
    check_activity_permission(activity_id, str(current_user.id), "view", db)

    # 获取辩题列表，按order排序
    debates = db.query(Debate).filter(
        Debate.activity_id == activity_id
    ).order_by(Debate.order.asc(), Debate.created_at.asc()).all()

    print(f"DEBUG: activity_id={activity_id}, found {len(debates)} debates")
    for debate in debates:
        print(f"DEBUG: debate id={debate.id}, title={debate.title}")

    # 转换为响应格式
    debate_list = [DebateResponse.model_validate(debate) for debate in debates]
    
    return {
        "success": True,
        "message": "获取辩题列表成功",
        "data": debate_list
    }


@router.post("/activities/{activity_id}/debates", status_code=201)
async def create_debate(
    activity_id: str,
    debate_data: DebateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建辩题"""
    # 检查权限
    check_activity_permission(activity_id, str(current_user.id), "edit", db)

    # 获取当前最大order值
    max_order = db.query(func.max(Debate.order)).filter(
        Debate.activity_id == activity_id
    ).scalar() or 0

    # 创建辩题
    debate_dict = debate_data.model_dump()
    print(f"DEBUG: Creating debate with data: {debate_dict}")
    print(f"DEBUG: activity_id={activity_id}, max_order={max_order}")
    
    debate = Debate(
        **debate_dict,
        activity_id=activity_id,
        order=max_order + 1
    )

    db.add(debate)
    db.commit()
    db.refresh(debate)

    print(f"DEBUG: Created debate with id={debate.id}, title={debate.title}")

    # 转换为响应格式
    debate_response = DebateResponse.model_validate(debate)
    
    return {
        "success": True,
        "message": "创建辩题成功",
        "data": debate_response
    }


@router.get("/debates/{debate_id}", response_model=DebateDetailResponse)
async def get_debate_detail(
    debate_id: str,
    db: Session = Depends(get_db)
):
    """获取辩题详情"""
    debate = db.query(Debate).filter(Debate.id == debate_id).first()
    if not debate:
        raise HTTPException(status_code=404, detail="Debate not found")

    # 获取投票统计
    vote_stats = get_debate_vote_stats(debate_id, db)

    # 构建响应
    debate_dict = DebateResponse.model_validate(debate).model_dump()
    return DebateDetailResponse(
        **debate_dict,
        vote_stats=vote_stats
    )


@router.put("/debates/{debate_id}", response_model=DebateResponse)
async def update_debate(
    debate_id: str,
    debate_data: DebateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新辩题"""
    debate = db.query(Debate).filter(Debate.id == debate_id).first()
    if not debate:
        raise HTTPException(status_code=404, detail="Debate not found")

    # 检查权限
    check_activity_permission(str(debate.activity_id),
                              str(current_user.id), "edit", db)

    # 更新字段
    update_data = debate_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(debate, field, value)

    db.commit()
    db.refresh(debate)

    return debate


@router.delete("/debates/{debate_id}")
async def delete_debate(
    debate_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除辩题"""
    debate = db.query(Debate).filter(Debate.id == debate_id).first()
    if not debate:
        raise HTTPException(status_code=404, detail="Debate not found")

    # 检查权限
    activity = check_activity_permission(
        str(debate.activity_id), str(current_user.id), "edit", db)

    # 检查是否为当前辩题
    current_debate_id = getattr(activity, 'current_debate_id')
    if current_debate_id and str(current_debate_id) == str(debate_id):
        raise HTTPException(
            status_code=400,
            detail="Cannot delete current debate. Please switch to another debate first."
        )

    db.delete(debate)
    db.commit()

    return {"message": "Debate deleted successfully"}


@router.put("/debates/{debate_id}/status")
async def update_debate_status(
    debate_id: str,
    status_data: DebateStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新辩题状态"""
    debate = db.query(Debate).filter(Debate.id == debate_id).first()
    if not debate:
        raise HTTPException(status_code=404, detail="Debate not found")

    # 检查权限
    check_activity_permission(str(debate.activity_id),
                              str(current_user.id), "control", db)

    # 更新状态
    setattr(debate, 'status', status_data.status)
    db.commit()

    return {"message": "Debate status updated successfully"}


@router.put("/debates/reorder")
async def reorder_debates(
    reorder_data: DebateReorder,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """调整辩题顺序"""
    if not reorder_data.debates:
        raise HTTPException(
            status_code=400, detail="Debates list cannot be empty")

    # 获取第一个辩题来确定活动ID和检查权限
    first_debate_id = reorder_data.debates[0].id
    if not first_debate_id:
        raise HTTPException(status_code=400, detail="Debate ID is required")

    first_debate = db.query(Debate).filter(
        Debate.id == first_debate_id).first()
    if not first_debate:
        raise HTTPException(status_code=404, detail="Debate not found")

    # 检查权限
    check_activity_permission(
        str(first_debate.activity_id), str(current_user.id), "edit", db)

    # 批量更新排序
    try:
        for debate_item in reorder_data.debates:
            debate_id = debate_item.id
            new_order = debate_item.order

            debate = db.query(Debate).filter(
                Debate.id == debate_id,
                Debate.activity_id == first_debate.activity_id
            ).first()

            if debate:
                setattr(debate, 'order', new_order)

        db.commit()
        return {"message": "Debates reordered successfully"}

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=400, detail="Failed to reorder debates")


@router.get("/activities/{activity_id}/current-debate", response_model=DebateDetailResponse)
async def get_current_debate(
    activity_id: str,
    db: Session = Depends(get_db)
):
    """获取当前辩题"""
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    current_debate_id = getattr(activity, 'current_debate_id')
    if not current_debate_id:
        raise HTTPException(status_code=404, detail="No current debate set")

    debate = db.query(Debate).filter(Debate.id == current_debate_id).first()
    if not debate:
        raise HTTPException(status_code=404, detail="Current debate not found")

    # 获取投票统计
    vote_stats = get_debate_vote_stats(str(debate.id), db)

    # 构建响应
    debate_dict = DebateResponse.model_validate(debate).model_dump()
    return DebateDetailResponse(
        **debate_dict,
        vote_stats=vote_stats
    )


@router.put("/activities/{activity_id}/current-debate")
async def set_current_debate(
    activity_id: str,
    current_debate_data: CurrentDebateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """切换当前辩题"""
    # 检查权限
    activity = check_activity_permission(
        activity_id, str(current_user.id), "control", db)

    # 验证辩题是否存在且属于该活动
    debate = db.query(Debate).filter(
        Debate.id == current_debate_data.debate_id,
        Debate.activity_id == activity_id
    ).first()

    if not debate:
        raise HTTPException(
            status_code=404, detail="Debate not found in this activity")

    # 更新当前辩题
    setattr(activity, 'current_debate_id', current_debate_data.debate_id)
    db.commit()

    return {"message": "Current debate updated successfully"}
