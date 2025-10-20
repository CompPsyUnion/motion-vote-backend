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
from src.services.activity_service import ActivityService
from src.schemas.screen import ScreenDisplayData, DisplayType
from src.schemas.base import ApiResponse

router = APIRouter()


@router.get("/{activity_id}/display", response_model=ApiResponse)
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

    # 组合为 ScreenDisplayData（让 pydantic 验证/格式化字段）
    display_payload = {
        "activity": activity_detail.model_dump(by_alias=True),
        "currentDebate": statistics.get("currentDebate"),
        "showData": statistics.get("currentDebateStats") is not None,
        "voteResults": statistics.get("currentDebateStats"),
        "timestamp": statistics.get("timestamp")
    }

    try:
        screen_data = ScreenDisplayData.model_validate(display_payload)
    except Exception:
        # 如果转换失败，仍返回基础统计数据作为降级处理
        return ApiResponse(success=True, data=statistics, message="获取成功")

    return ApiResponse(success=True, data=screen_data.model_dump(by_alias=True), message="获取成功")
