"""大屏 API 端点

基于 OpenAPI 规范实现的大屏显示和控制接口，包括：
- 获取大屏统计数据
- 获取房间连接信息
- 触发各类广播事件
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.dependencies import get_db
from src.services.screen_service import ScreenService

router = APIRouter()


@router.get("/statistics/{activity_id}")
async def get_screen_statistics(
    activity_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """获取大屏统计数据（从Redis缓存读取）

    包括：实时投票数据、当前辩题、正反方得分等
    """
    try:
        screen_service = ScreenService(db)
        statistics = await screen_service.get_screen_statistics(activity_id)

        return {
            "success": True,
            "data": statistics,
            "message": "统计数据获取成功"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/room-info/{activity_id}")
async def get_room_info(
    activity_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """获取大屏房间连接信息"""
    screen_service = ScreenService(db)
    room_info = screen_service.get_room_info(activity_id)
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
    """手动触发投票更新广播

    已整合到统计数据更新中
    """
    screen_service = ScreenService(db)
    await screen_service.trigger_vote_update_broadcast(
        activity_id, debate_id, vote_data
    )

    return {
        "success": True,
        "message": "投票更新已广播"
    }


@router.post("/broadcast/statistics")
async def trigger_statistics_broadcast(
    activity_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """手动触发统计数据广播"""
    screen_service = ScreenService(db)
    await screen_service.trigger_statistics_broadcast(activity_id)

    return {
        "success": True,
        "message": "统计数据已广播"
    }


@router.post("/broadcast/debate-change")
async def trigger_debate_change_broadcast(
    activity_id: str,
    debate_data: Dict[str, Any],
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """广播辩题切换"""
    screen_service = ScreenService(db)
    await screen_service.trigger_debate_change_broadcast(activity_id, debate_data)
    return {
        "success": True,
        "message": "辩题切换已广播"
    }


@router.post("/broadcast/debate-status")
async def trigger_debate_status_broadcast(
    activity_id: str,
    debate_id: str,
    status: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """广播辩题状态变更"""
    screen_service = ScreenService(db)
    await screen_service.trigger_debate_status_broadcast(
        activity_id, debate_id, status
    )
    return {
        "success": True,
        "message": "辩题状态变更已广播"
    }
