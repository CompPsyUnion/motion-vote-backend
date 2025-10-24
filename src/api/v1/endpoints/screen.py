"""大屏 API 端点

基于 OpenAPI 规范实现的大屏显示和控制接口，包括：
- 获取大屏统计数据
- 获取房间连接信息
- 触发各类广播事件
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from src.api.dependencies import get_current_user, get_db
from src.core.websocket_manager import screen_manager
from src.models.user import User
from src.schemas.base import ApiResponse
from src.schemas.screen import DisplayType, ScreenDisplayData
from src.services.activity_service import ActivityService
from src.services.screen_service import ScreenService

router = APIRouter()


class ScreenControlRequest(BaseModel):
    """大屏控制请求"""
    action: str = Field(...,
                        description="控制动作: toggle_cover_page, next_stage, previous_stage")


@router.get("/{activity_id}/display", response_model=ApiResponse)
@router.get("/{activity_id}/display/", response_model=ApiResponse)
async def get_screen_display(
    activity_id: str,
    type: DisplayType = DisplayType.both_sides,
    db: Session = Depends(get_db)
) -> ApiResponse:
    """获取大屏显示数据

    按 openapi.json 定义，仅用于前端在进入大屏页面时做一次初始化查询。
    如果活动不存在返回 404。
    """
    # 验证活动是否存在（ActivityService 会抛出 404）
    activity_service = ActivityService(db)
    try:
        activity_detail = activity_service.get_activity_detail(
            activity_id, None)
    except HTTPException as e:
        # 直接将 404 透传给客户端
        raise e

    # 获取实时统计数据（可能来自 Redis 缓存）
    screen_service = ScreenService(db)
    try:
        statistics = await screen_service.get_screen_statistics(activity_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # 简化返回数据结构，只返回用户要求的字段
    simplified_data = {
        "activityId": activity_detail.id,
        "activityName": activity_detail.name,
        "activityStatus": activity_detail.status,
        "currentDebate": statistics.get("currentDebate"),
        "currentDebateStats": statistics.get("currentDebateStats"),
        "timestamp": statistics.get("timestamp")
    }

    return ApiResponse(success=True, data=simplified_data, message="获取成功")


@router.post("/{activity_id}/control", response_model=ApiResponse)
@router.post("/{activity_id}/control/", response_model=ApiResponse)
async def control_screen(
    activity_id: str,
    control_data: ScreenControlRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ApiResponse:
    """大屏控制 - 远程控制大屏显示内容

    支持的控制动作:
    - toggle_cover_page: 切换封面页显示
    - next_stage: 下一个阶段
    - previous_stage: 上一个阶段
    """
    # 验证活动权限
    activity_service = ActivityService(db)
    activity_service.check_activity_permission(
        activity_id, "control", current_user)

    # 验证动作
    valid_actions = ["toggle_cover_page", "next_stage", "previous_stage"]
    if control_data.action not in valid_actions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action. Must be one of: {', '.join(valid_actions)}"
        )

    # 通过 WebSocket 广播控制指令
    message = {
        "type": "screen_control",
        "action": control_data.action,
        "activity_id": activity_id,
        "timestamp": __import__("datetime").datetime.now().isoformat()
    }

    await screen_manager.broadcast_to_room(activity_id, message)

    return ApiResponse(
        success=True,
        message=f"Screen control command '{control_data.action}' sent successfully"
    )
