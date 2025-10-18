from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any

from src.api.dependencies import get_db
from src.services.statistics_service import get_statistics_service
from src.core.socketio_manager import (
    broadcast_statistics_update,
    broadcast_debate_change,
    broadcast_debate_status,
    screen_manager
)

router = APIRouter()


@router.get("/statistics/{activity_id}")
async def get_screen_statistics(
    activity_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    获取大屏统计数据（从Redis缓存读取）
    包括：实时投票数据、当前辩题、正反方得分等
    """
    try:
        # 从Redis缓存获取统计数据
        stats_service = get_statistics_service(db)
        statistics = await stats_service.get_activity_statistics(activity_id)

        return {
            "success": True,
            "data": statistics,
            "message": "统计数据获取成功"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/room-info/{activity_id}")
async def get_room_info(activity_id: str) -> Dict[str, Any]:
    """获取大屏房间连接信息"""
    room_info = screen_manager.get_room_info(activity_id)
    return {
        "success": True,
        "data": room_info,
        "message": "房间信息获取成功"
    }


@router.post("/broadcast/vote-update")
async def trigger_vote_update_broadcast(
    activity_id: str,
    debate_id: str,
    vote_data: Dict[str, Any],
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    手动触发投票更新广播
    已整合到统计数据更新中
    """
    # 更新统计缓存并广播
    stats_service = get_statistics_service(db)
    await stats_service.update_statistics_cache(activity_id, debate_id)

    return {
        "success": True,
        "message": "投票更新已广播"
    }


@router.post("/broadcast/statistics")
async def trigger_statistics_broadcast(
    activity_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    手动触发统计数据广播
    """
    stats_service = get_statistics_service(db)
    await stats_service.update_statistics_cache(activity_id)

    return {
        "success": True,
        "message": "统计数据已广播"
    }


@router.post("/broadcast/debate-change")
async def trigger_debate_change_broadcast(
    activity_id: str,
    debate_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    广播辩题切换
    """
    await broadcast_debate_change(activity_id, debate_data)
    return {
        "success": True,
        "message": "辩题切换已广播"
    }


@router.post("/broadcast/debate-status")
async def trigger_debate_status_broadcast(
    activity_id: str,
    debate_id: str,
    status: str
) -> Dict[str, Any]:
    """
    广播辩题状态变更
    """
    await broadcast_debate_status(activity_id, debate_id, status)
    return {
        "success": True,
        "message": "辩题状态变更已广播"
    }
