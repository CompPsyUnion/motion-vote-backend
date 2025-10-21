"""辩题独立资源管理 API 端点

基于 OpenAPI 规范实现的辩题独立资源接口，包括：
- 单个辩题的详细操作 (GET, PUT, DELETE)
- 辩题状态管理
- 辩题排序

注意：
- /api/activities/{activityId}/debates 路由在 activities.py 中
- 这里只处理 /api/debates/* 独立资源路由
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.api.dependencies import get_current_user, get_db
from src.models.user import User
from src.schemas.debate import (DebateReorder, DebateStatusUpdate,
                                DebateUpdate)
from src.services.activity_service import ActivityService
from src.services.debate_service import DebateService

router = APIRouter()


@router.get("/{debate_id}")
@router.get("/{debate_id}/")
async def get_debate_detail(
    debate_id: str,
    db: Session = Depends(get_db)
):
    """获取辩题详情"""
    debate_service = DebateService(db)
    debate_detail = debate_service.get_debate_detail(debate_id)

    return {
        "success": True,
        "message": "获取辩题详情成功",
        "data": debate_detail
    }


@router.put("/{debate_id}")
@router.put("/{debate_id}/")
async def update_debate(
    debate_id: str,
    debate_data: DebateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新辩题"""
    debate_service = DebateService(db)
    debate = debate_service.get_debate_by_id(debate_id)

    # 检查权限
    activity_service = ActivityService(db)
    activity_service.check_activity_permission(
        str(debate.activity_id), "edit", current_user
    )

    # 更新辩题
    debate_service.update_debate(debate_id, debate_data)

    return {
        "success": True,
        "message": "更新辩题成功"
    }


@router.delete("/{debate_id}")
@router.delete("/{debate_id}/")
async def delete_debate(
    debate_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除辩题"""
    debate_service = DebateService(db)
    debate = debate_service.get_debate_by_id(debate_id)

    # 检查权限
    activity_service = ActivityService(db)
    activity_service.check_activity_permission(
        str(debate.activity_id), "edit", current_user
    )

    # 删除辩题
    debate_service.delete_debate(debate_id)

    return {
        "success": True,
        "message": "删除辩题成功"
    }


@router.put("/{debate_id}/status")
@router.put("/{debate_id}/status/")
async def update_debate_status(
    debate_id: str,
    status_data: DebateStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新辩题状态"""
    debate_service = DebateService(db)
    debate = debate_service.get_debate_by_id(debate_id)

    # 检查权限
    activity_service = ActivityService(db)
    activity_service.check_activity_permission(
        str(debate.activity_id), "control", current_user
    )

    # 更新状态
    debate_service.update_debate_status(debate_id, status_data)

    return {
        "success": True,
        "message": "Debate status updated successfully"
    }


@router.put("/reorder")
@router.put("/reorder/")
async def reorder_debates(
    reorder_data: DebateReorder,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """调整辩题顺序"""
    debate_service = DebateService(db)

    # 获取第一个辩题来确定活动ID并检查权限
    if not reorder_data.debates:
        return {
            "success": False,
            "message": "No debates provided"
        }

    first_debate = debate_service.get_debate_by_id(reorder_data.debates[0].id)

    # 检查权限
    activity_service = ActivityService(db)
    activity_service.check_activity_permission(
        str(first_debate.activity_id), "edit", current_user
    )

    # 批量更新顺序
    debate_service.reorder_debates(reorder_data)

    return {
        "success": True,
        "message": "辩题排序更新成功"
    }
