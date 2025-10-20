"""
WebSocket Manager for real-time screen updates
大屏实时数据推送管理器 - 使用原生 WebSocket
"""
from datetime import datetime
import json
import logging
from typing import Any, Dict, Optional, Set
import traceback
import uuid

from fastapi import WebSocket, WebSocketDisconnect
from src.config import settings
from src.utils.logger import websocket_logger


class ScreenWebSocketManager:
    """大屏 WebSocket 连接管理器"""

    def __init__(self):
        # 存储所有活动连接 {connection_id: WebSocket}
        self.active_connections: Dict[str, WebSocket] = {}
        # 存储房间信息 {activity_id: Set[connection_id]}
        self.rooms: Dict[str, Set[str]] = {}
        # 存储连接到活动的映射 {connection_id: activity_id}
        self.connection_activities: Dict[str, str] = {}
        # 存储连接的用户信息 {connection_id: user_info}
        self.connection_info: Dict[str, Dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket, activity_id: Optional[str] = None) -> str:
        """接受 WebSocket 连接并返回连接 ID"""
        await websocket.accept()
        connection_id = str(uuid.uuid4())
        self.active_connections[connection_id] = websocket

        websocket_logger.info(f"✅ WebSocket connected: {connection_id}")

        # 发送连接成功消息
        await self.send_personal_message(connection_id, {
            'type': 'connection_status',
            'status': 'connected',
            'connection_id': connection_id,
            'timestamp': datetime.now().isoformat()
        })

        # 如果指定了活动 ID，自动加入房间
        if activity_id:
            await self.join_room(connection_id, activity_id)

        return connection_id

    def disconnect(self, connection_id: str):
        """断开连接"""
        try:
            # 从房间中移除
            if connection_id in self.connection_activities:
                activity_id = self.connection_activities[connection_id]
                if activity_id in self.rooms:
                    self.rooms[activity_id].discard(connection_id)
                    if not self.rooms[activity_id]:
                        del self.rooms[activity_id]
                del self.connection_activities[connection_id]

            # 移除连接信息
            if connection_id in self.connection_info:
                del self.connection_info[connection_id]

            # 移除连接
            if connection_id in self.active_connections:
                del self.active_connections[connection_id]

            websocket_logger.info(f"🔌 WebSocket disconnected: {connection_id}")
        except Exception as e:
            websocket_logger.error(
                f"❌ Error disconnecting {connection_id}: {e}")

    async def join_room(self, connection_id: str, activity_id: str, user_info: Optional[Dict] = None):
        """加入房间"""
        try:
            # 如果已经在其他房间，先离开
            if connection_id in self.connection_activities:
                old_activity_id = self.connection_activities[connection_id]
                if old_activity_id != activity_id:
                    await self.leave_room(connection_id)

            # 加入新房间
            if activity_id not in self.rooms:
                self.rooms[activity_id] = set()

            self.rooms[activity_id].add(connection_id)
            self.connection_activities[connection_id] = activity_id

            if user_info:
                self.connection_info[connection_id] = user_info

            # 发送加入成功消息
            await self.send_personal_message(connection_id, {
                'type': 'joined_screen',
                'activity_id': activity_id,
                'connection_id': connection_id,
                'timestamp': datetime.now().isoformat()
            })

            websocket_logger.info(
                f"✅ Connection {connection_id} joined room: {activity_id}")
        except Exception as e:
            websocket_logger.error(f"❌ Error joining room: {e}")
            websocket_logger.error(traceback.format_exc())

    async def leave_room(self, connection_id: str):
        """离开房间"""
        try:
            if connection_id not in self.connection_activities:
                return

            activity_id = self.connection_activities[connection_id]

            if activity_id in self.rooms:
                self.rooms[activity_id].discard(connection_id)
                if not self.rooms[activity_id]:
                    del self.rooms[activity_id]

            del self.connection_activities[connection_id]

            # 发送离开消息
            await self.send_personal_message(connection_id, {
                'type': 'left_screen',
                'activity_id': activity_id,
                'connection_id': connection_id,
                'timestamp': datetime.now().isoformat()
            })

            websocket_logger.info(
                f"📤 Connection {connection_id} left room: {activity_id}")
        except Exception as e:
            websocket_logger.error(f"❌ Error leaving room: {e}")

    async def send_personal_message(self, connection_id: str, message: Dict[str, Any]):
        """发送消息给特定连接"""
        try:
            if connection_id in self.active_connections:
                websocket = self.active_connections[connection_id]
                await websocket.send_text(json.dumps(message))
        except Exception as e:
            websocket_logger.error(
                f"❌ Error sending message to {connection_id}: {e}")
            # 如果发送失败，断开连接
            self.disconnect(connection_id)

    async def broadcast_to_room(self, activity_id: str, message: Dict[str, Any]):
        """向房间内所有连接广播消息"""
        if activity_id not in self.rooms:
            return

        disconnected = []
        for connection_id in self.rooms[activity_id]:
            try:
                if connection_id in self.active_connections:
                    websocket = self.active_connections[connection_id]
                    await websocket.send_text(json.dumps(message))
            except Exception as e:
                websocket_logger.error(
                    f"❌ Error broadcasting to {connection_id}: {e}")
                disconnected.append(connection_id)

        # 清理断开的连接
        for connection_id in disconnected:
            self.disconnect(connection_id)

        websocket_logger.info(
            f"📢 Broadcasted to room {activity_id}: {len(self.rooms.get(activity_id, []))} connections")

    def get_room_info(self, activity_id: str) -> Dict[str, Any]:
        """获取房间信息"""
        if activity_id not in self.rooms:
            return {"activity_id": activity_id, "connections": 0, "users": []}

        connection_ids = self.rooms[activity_id]
        users = [self.connection_info.get(cid, {}) for cid in connection_ids]

        return {
            "activity_id": activity_id,
            "connections": len(connection_ids),
            "users": users
        }

    def get_activity_id(self, connection_id: str) -> Optional[str]:
        """根据连接ID获取活动ID"""
        return self.connection_activities.get(connection_id)


# 全局管理器实例
screen_manager = ScreenWebSocketManager()


# 广播函数
async def broadcast_to_screen(activity_id: str, event: str, data: Dict[str, Any]):
    """向指定活动的所有大屏客户端广播数据"""
    try:
        message = {
            'event': event,
            **data
        }
        await screen_manager.broadcast_to_room(activity_id, message)
        websocket_logger.info(f"📢 Broadcasted {event} to room {activity_id}")
    except Exception as e:
        websocket_logger.error(f"❌ Error broadcasting to screen: {e}")
        websocket_logger.error(traceback.format_exc())


# 专用广播函数
async def broadcast_vote_update(activity_id: str, debate_id: str, vote_data: Dict[str, Any]):
    """广播投票更新"""
    await broadcast_to_screen(activity_id, 'vote_update', {
        'type': 'vote_update',
        'activity_id': activity_id,
        'debate_id': debate_id,
        'data': vote_data,
        'timestamp': datetime.now().isoformat()
    })


async def broadcast_statistics_update(activity_id: str, statistics: Dict[str, Any]):
    """广播统计数据更新"""
    await broadcast_to_screen(activity_id, 'statistics_update', {
        'type': 'statistics_update',
        'activity_id': activity_id,
        'data': statistics,
        'timestamp': datetime.now().isoformat()
    })


async def broadcast_debate_change(activity_id: str, debate_data: Dict[str, Any]):
    """广播辩题切换"""
    await broadcast_to_screen(activity_id, 'debate_change', {
        'type': 'debate_change',
        'activity_id': activity_id,
        'data': debate_data,
        'timestamp': datetime.now().isoformat()
    })


async def broadcast_debate_status(activity_id: str, debate_id: str, status: str):
    """广播辩题状态变更"""
    await broadcast_to_screen(activity_id, 'debate_status', {
        'type': 'debate_status',
        'activity_id': activity_id,
        'debate_id': debate_id,
        'status': status,
        'timestamp': datetime.now().isoformat()
    })
