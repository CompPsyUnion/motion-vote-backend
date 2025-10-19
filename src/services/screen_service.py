"""大屏服务层

处理大屏显示和控制相关的业务逻辑，包括：
- 获取大屏统计数据
- 获取房间连接信息
- 触发各类广播事件（投票更新、统计数据、辩题切换、状态变更）
"""

from typing import Any, Dict

from sqlalchemy.orm import Session

from src.core.socketio_manager import (broadcast_debate_change,
                                       broadcast_debate_status,
                                       screen_manager)
from src.services.statistics_service import get_statistics_service


class ScreenService:
    """大屏服务类"""

    def __init__(self, db: Session):
        """初始化大屏服务

        Args:
            db: 数据库会话
        """
        self.db = db

    async def get_screen_statistics(self, activity_id: str) -> Dict[str, Any]:
        """获取大屏统计数据（从Redis缓存读取）

        包括：实时投票数据、当前辩题、正反方得分等

        Args:
            activity_id: 活动ID

        Returns:
            Dict[str, Any]: 统计数据

        Raises:
            HTTPException: 获取统计数据失败
        """
        # 从Redis缓存获取统计数据
        stats_service = get_statistics_service(self.db)
        statistics = await stats_service.get_activity_statistics(activity_id)
        return statistics

    def get_room_info(self, activity_id: str) -> Dict[str, Any]:
        """获取大屏房间连接信息

        Args:
            activity_id: 活动ID

        Returns:
            Dict[str, Any]: 房间信息
        """
        room_info = screen_manager.get_room_info(activity_id)
        return room_info

    async def trigger_vote_update_broadcast(
        self,
        activity_id: str,
        debate_id: str,
        vote_data: Dict[str, Any]
    ) -> None:
        """手动触发投票更新广播

        已整合到统计数据更新中

        Args:
            activity_id: 活动ID
            debate_id: 辩题ID
            vote_data: 投票数据
        """
        # 更新统计缓存并广播
        stats_service = get_statistics_service(self.db)
        await stats_service.update_statistics_cache(activity_id, debate_id)

    async def trigger_statistics_broadcast(self, activity_id: str) -> None:
        """手动触发统计数据广播

        Args:
            activity_id: 活动ID
        """
        stats_service = get_statistics_service(self.db)
        await stats_service.update_statistics_cache(activity_id)

    async def trigger_debate_change_broadcast(
        self,
        activity_id: str,
        debate_data: Dict[str, Any]
    ) -> None:
        """广播辩题切换

        Args:
            activity_id: 活动ID
            debate_data: 辩题数据
        """
        await broadcast_debate_change(activity_id, debate_data)

    async def trigger_debate_status_broadcast(
        self,
        activity_id: str,
        debate_id: str,
        status: str
    ) -> None:
        """广播辩题状态变更

        Args:
            activity_id: 活动ID
            debate_id: 辩题ID
            status: 新状态
        """
        await broadcast_debate_status(activity_id, debate_id, status)
