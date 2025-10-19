from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from src.api.dependencies import get_current_user, get_db
from src.models.activity import Activity, Collaborator
from src.models.debate import Debate
from src.models.user import User
from src.models.vote import Vote
from src.schemas.debate import (CurrentDebateUpdate, DebateCreate,
                                DebateDetailResponse, DebateReorder,
                                DebateResponse, DebateStatusUpdate,
                                DebateUpdate, VoteStats)
from src.schemas.vote import VotePosition
from src.schemas.base import ApiResponse

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
        Collaborator.user_id == user_id
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
    from src.models.vote import Vote, VoteHistory

    # 分别统计各种投票数量 - 使用更简单的查询方法
    total_votes = db.query(func.count(Vote.id)).filter(
        Vote.debate_id == debate_id).scalar() or 0
    pro_votes = db.query(func.count(Vote.id)).filter(
        Vote.debate_id == debate_id,
        Vote.position == VotePosition.pro
    ).scalar() or 0
    con_votes = db.query(func.count(Vote.id)).filter(
        Vote.debate_id == debate_id,
        Vote.position == VotePosition.con
    ).scalar() or 0
    abstain_votes = db.query(func.count(Vote.id)).filter(
        Vote.debate_id == debate_id,
        Vote.position == VotePosition.abstain
    ).scalar() or 0

    # 计算初始票数：从VoteHistory中获取每个投票的第一个位置
    # 如果没有历史记录，则使用当前位置作为初始位置
    votes_with_history = db.query(Vote).filter(
        Vote.debate_id == debate_id).all()

    pro_previous_votes = 0
    con_previous_votes = 0
    abstain_previous_votes = 0

    # 统计从各方到其他方的人数
    pro_to_con = 0
    pro_to_abstain = 0
    con_to_pro = 0
    con_to_abstain = 0
    abstain_to_pro = 0
    abstain_to_con = 0

    for vote in votes_with_history:
        # 获取该投票的最早历史记录
        first_history = db.query(VoteHistory).filter(
            VoteHistory.vote_id == vote.id
        ).order_by(VoteHistory.created_at.asc()).first()

        if first_history:
            # 使用历史记录中的第一个位置
            initial_position = getattr(first_history, 'new_position')
        else:
            # 没有历史记录，说明从未改过票，使用当前位置
            initial_position = getattr(vote, 'position')

        # 当前位置
        current_position = getattr(vote, 'position')

        # 统计初始票数
        if initial_position == VotePosition.pro:
            pro_previous_votes += 1
        elif initial_position == VotePosition.con:
            con_previous_votes += 1
        elif initial_position == VotePosition.abstain:
            abstain_previous_votes += 1

        # 统计转换情况（初始位置和当前位置不同）
        if initial_position != current_position:
            if initial_position == VotePosition.pro and current_position == VotePosition.con:
                pro_to_con += 1
            elif initial_position == VotePosition.pro and current_position == VotePosition.abstain:
                pro_to_abstain += 1
            elif initial_position == VotePosition.con and current_position == VotePosition.pro:
                con_to_pro += 1
            elif initial_position == VotePosition.con and current_position == VotePosition.abstain:
                con_to_abstain += 1
            elif initial_position == VotePosition.abstain and current_position == VotePosition.pro:
                abstain_to_pro += 1
            elif initial_position == VotePosition.abstain and current_position == VotePosition.con:
                abstain_to_con += 1

    # 计算弃权百分比
    abstain_percentage = (abstain_votes / total_votes *
                          100) if total_votes > 0 else 0

    # 计算得分（根据新规则）
    # 正方得分 = 反方到正方人数/反方初始人数 * 1000 + 中立到正方人数/中立初始人数 * 500
    pro_score = 0.0
    if con_previous_votes > 0:
        pro_score += (con_to_pro / con_previous_votes * 1000)
    if abstain_previous_votes > 0:
        pro_score += (abstain_to_pro / abstain_previous_votes * 500)

    # 反方得分 = 正方到反方人数/正方初始人数 * 1000 + 中立到反方人数/中立初始人数 * 500
    con_score = 0.0
    if pro_previous_votes > 0:
        con_score += (pro_to_con / pro_previous_votes * 1000)
    if abstain_previous_votes > 0:
        con_score += (abstain_to_con / abstain_previous_votes * 500)

    return VoteStats(
        total_votes=total_votes,
        pro_votes=pro_votes,
        con_votes=con_votes,
        abstain_votes=abstain_votes,
        abstain_percentage=round(abstain_percentage, 2),
        pro_previous_votes=pro_previous_votes,
        con_previous_votes=con_previous_votes,
        abstain_previous_votes=abstain_previous_votes,
        pro_to_con_votes=pro_to_con,
        con_to_pro_votes=con_to_pro,
        abstain_to_pro_votes=abstain_to_pro,
        abstain_to_con_votes=abstain_to_con,
        pro_score=round(pro_score, 2),
        con_score=round(con_score, 2)
    )


@router.get("/activities/{activity_id}/debates")
async def get_debates(
    activity_id: str,
    search: Optional[str] = Query(
        default=None, description="搜索关键词 - 支持辩题标题、描述模糊匹配"),
    status: Optional[str] = Query(
        default=None, description="辩题状态筛选 (draft|active|locked|archived)"),
    page: int = Query(default=1, ge=1, description="页码"),
    limit: int = Query(default=50, ge=1, le=100, description="每页数量"),
    sort_by: Optional[str] = Query(
        default="order", description="排序字段 (order|created_at|title)"),
    sort_order: Optional[str] = Query(
        default="asc", description="排序方向 (asc|desc)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取辩题列表

    支持多种筛选和搜索方式：
    - search: 全文搜索(标题、描述)
    - status: 状态筛选
    - page/limit: 分页控制
    - sort_by/sort_order: 自定义排序
    """
    from math import ceil

    from sqlalchemy import asc, desc, or_

    # 检查权限
    check_activity_permission(activity_id, str(current_user.id), "view", db)

    # 构建查询
    query = db.query(Debate).filter(Debate.activity_id == activity_id)

    # 搜索筛选
    if search and search.strip():
        search_terms = search.strip().split()
        search_conditions = []
        for term in search_terms:
            term_pattern = f"%{term}%"
            search_conditions.append(
                or_(
                    Debate.title.ilike(term_pattern),
                    Debate.description.ilike(term_pattern)
                )
            )
        if search_conditions:
            query = query.filter(*search_conditions)

    # 状态筛选
    if status and status.strip():
        try:
            from src.schemas.debate import DebateStatus
            status_enum = DebateStatus(status.strip().lower())
            query = query.filter(Debate.status == status_enum)
        except ValueError:
            pass  # 忽略无效状态

    # 排序
    sort_column = Debate.order  # 默认按order排序
    if sort_by == "created_at":
        sort_column = Debate.created_at
    elif sort_by == "title":
        sort_column = Debate.title
    elif sort_by == "order":
        sort_column = Debate.order

    if sort_order == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))

    # 分页
    total = query.count()
    debates = query.offset((page - 1) * limit).limit(limit).all()

    # 转换为响应格式
    debate_list = [DebateResponse.model_validate(debate) for debate in debates]

    return {
        "success": True,
        "message": "获取辩题列表成功",
        "data": {
            "items": debate_list,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": ceil(total / limit) if limit > 0 else 0
        }
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
    debate = Debate(
        **debate_dict,
        activity_id=activity_id,
        order=max_order + 1
    )

    db.add(debate)
    db.commit()
    db.refresh(debate)

    # 转换为响应格式
    debate_response = DebateResponse.model_validate(debate)

    return {
        "success": True,
        "message": "创建辩题成功",
        "data": debate_response
    }


@router.get("/debates/{debate_id}")
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
    debate_detail = DebateDetailResponse(
        **debate_dict,
        vote_stats=vote_stats
    )

    return {
        "success": True,
        "message": "获取辩题详情成功",
        "data": debate_detail
    }


@router.put("/debates/{debate_id}")
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

    # 逐个更新字段以避免类型问题
    if update_data:
        for field, value in update_data.items():
            if hasattr(debate, field):
                db.query(Debate).filter(
                    Debate.id == debate_id).update({field: value})

    db.commit()

    # 重新获取更新后的辩题
    updated_debate = db.query(Debate).filter(Debate.id == debate_id).first()

    # 如果更新了activity_id或status,清除Redis缓存
    if 'activity_id' in update_data or 'status' in update_data:
        from src.services.vote_service import VoteService
        service = VoteService(db)
        service.invalidate_debate_cache(debate_id)

    return {
        "success": True,
        "message": "更新辩题成功"
    }


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
    check_activity_permission(
        str(debate.activity_id), str(current_user.id), "edit", db)

    # 检查是否为当前辩题
    activity = db.query(Activity).filter(
        Activity.id == debate.activity_id).first()
    current_debate_id = getattr(activity, 'current_debate_id')
    if current_debate_id and str(current_debate_id) == str(debate_id):
        # 清除当前辩题
        setattr(activity, 'current_debate_id', None)

    # 删除辩题
    db.delete(debate)
    db.commit()

    return {
        "success": True,
        "message": "删除辩题成功"
    }


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

    # 清除Redis缓存
    from src.services.vote_service import VoteService
    service = VoteService(db)
    service.invalidate_debate_cache(debate_id)

    return {"message": "Debate status updated successfully"}


@router.put("/debates/reorder")
async def reorder_debates(
    reorder_data: DebateReorder,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """调整辩题顺序"""
    # 这里需要验证所有辩题都属于同一个活动
    if not reorder_data.debates:
        raise HTTPException(status_code=400, detail="No debates provided")

    # 获取第一个辩题来确定活动ID
    first_debate = db.query(Debate).filter(
        Debate.id == reorder_data.debates[0].id
    ).first()

    if not first_debate:
        raise HTTPException(status_code=404, detail="Debate not found")

    # 检查权限
    check_activity_permission(
        str(first_debate.activity_id), str(current_user.id), "edit", db)

    # 批量更新顺序
    for item in reorder_data.debates:
        db.query(Debate).filter(Debate.id == item.id).update(
            {"order": item.order})

    db.commit()
    return {
        "success": True,
        "message": "辩题排序更新成功"
    }


@router.get("/activities/{activity_id}/current-debate", response_model=ApiResponse)
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
    debate_detail = DebateDetailResponse(
        **debate_dict,
        vote_stats=vote_stats
    )

    # 返回时将内部 Pydantic 模型序列化为使用别名的 dict
    return {
        "success": True,
        "message": "获取当前辩题成功",
        "data": debate_detail.model_dump(by_alias=True)
    }


@router.put("/activities/{activity_id}/current-debate")
async def set_current_debate(
    activity_id: str,
    current_debate_data: CurrentDebateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """切换当前辩题"""
    from datetime import datetime

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

    # 获取之前的当前辩题
    old_debate_id = getattr(activity, 'current_debate_id', None)

    # 如果有之前的辩题，标记为结束
    if old_debate_id and old_debate_id != current_debate_data.debate_id:
        old_debate = db.query(Debate).filter(
            Debate.id == old_debate_id).first()
        if old_debate:
            old_ended_at = getattr(old_debate, 'ended_at', None)
            if not old_ended_at:
                setattr(old_debate, 'ended_at', datetime.now())

    # 标记新辩题开始
    debate_started_at = getattr(debate, 'started_at', None)
    if not debate_started_at:
        setattr(debate, 'started_at', datetime.now())

    # 更新当前辩题
    db.query(Activity).filter(Activity.id == activity_id).update({
        "current_debate_id": current_debate_data.debate_id
    })
    db.commit()

    return {
        "success": True,
        "message": "当前辩题切换成功"
    }
