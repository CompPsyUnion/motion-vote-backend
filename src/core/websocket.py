import json
import uuid
from typing import Dict

from fastapi import WebSocket, WebSocketDisconnect


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        # 存储活动连接 {activity_id: {connection_id: websocket}}
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}
        # 存储连接对应的活动ID {connection_id: activity_id}
        self.connection_activities: Dict[str, str] = {}

    async def connect(self, websocket: WebSocket, activity_id: str) -> str:
        """建立连接"""
        await websocket.accept()

        connection_id = str(uuid.uuid4())

        if activity_id not in self.active_connections:
            self.active_connections[activity_id] = {}

        self.active_connections[activity_id][connection_id] = websocket
        self.connection_activities[connection_id] = activity_id

        # 发送连接成功消息
        await websocket.send_text(json.dumps({
            "type": "connection_established",
            "connection_id": connection_id,
            "activity_id": activity_id,
            "message": "连接建立成功"
        }))

        return connection_id

    def disconnect(self, connection_id: str):
        """断开连接"""
        if connection_id in self.connection_activities:
            activity_id = self.connection_activities[connection_id]

            if (activity_id in self.active_connections and
                    connection_id in self.active_connections[activity_id]):
                del self.active_connections[activity_id][connection_id]

                # 如果该活动没有其他连接，清理活动记录
                if not self.active_connections[activity_id]:
                    del self.active_connections[activity_id]

            del self.connection_activities[connection_id]

    async def send_personal_message(self, message: str, connection_id: str):
        """发送个人消息"""
        if connection_id in self.connection_activities:
            activity_id = self.connection_activities[connection_id]
            if (activity_id in self.active_connections and
                    connection_id in self.active_connections[activity_id]):
                websocket = self.active_connections[activity_id][connection_id]
                await websocket.send_text(message)

    async def broadcast_to_activity(self, message: str, activity_id: str):
        """向指定活动的所有连接广播消息"""
        if activity_id in self.active_connections:
            disconnected_connections = []

            for connection_id, websocket in self.active_connections[activity_id].items():
                try:
                    await websocket.send_text(message)
                except:
                    # 连接已断开，记录下来稍后清理
                    disconnected_connections.append(connection_id)

            # 清理断开的连接
            for connection_id in disconnected_connections:
                self.disconnect(connection_id)

    async def broadcast_vote_update(self, activity_id: str, debate_id: str, vote_data: dict):
        """广播投票更新"""
        message = json.dumps({
            "type": "vote_update",
            "activity_id": activity_id,
            "debate_id": debate_id,
            "data": vote_data,
            "timestamp": vote_data.get("timestamp")
        })
        await self.broadcast_to_activity(message, activity_id)

    async def broadcast_debate_status_change(self, activity_id: str, debate_id: str, status: str):
        """广播辩题状态变更"""
        message = json.dumps({
            "type": "debate_status_change",
            "activity_id": activity_id,
            "debate_id": debate_id,
            "status": status,
            "timestamp": str(uuid.uuid4())  # 简单的时间戳
        })
        await self.broadcast_to_activity(message, activity_id)

    async def broadcast_current_debate_change(self, activity_id: str, debate_id: str, debate_data: dict):
        """广播当前辩题切换"""
        message = json.dumps({
            "type": "current_debate_change",
            "activity_id": activity_id,
            "debate_id": debate_id,
            "data": debate_data,
            "timestamp": str(uuid.uuid4())  # 简单的时间戳
        })
        await self.broadcast_to_activity(message, activity_id)

    def get_activity_connection_count(self, activity_id: str) -> int:
        """获取指定活动的连接数"""
        if activity_id in self.active_connections:
            return len(self.active_connections[activity_id])
        return 0

    def get_all_activity_stats(self) -> Dict[str, int]:
        """获取所有活动的连接统计"""
        return {
            activity_id: len(connections)
            for activity_id, connections in self.active_connections.items()
        }


# 全局连接管理器实例
manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket, activity_id: str):
    """WebSocket 端点处理函数"""
    connection_id = await manager.connect(websocket, activity_id)

    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                message_type = message.get("type")

                # 处理不同类型的消息
                if message_type == "ping":
                    # 心跳检测
                    await manager.send_personal_message(
                        json.dumps(
                            {"type": "pong", "timestamp": message.get("timestamp")}),
                        connection_id
                    )

                elif message_type == "subscribe_vote_updates":
                    # 订阅投票更新（可以在这里做一些订阅逻辑）
                    await manager.send_personal_message(
                        json.dumps({
                            "type": "subscription_confirmed",
                            "subscription": "vote_updates"
                        }),
                        connection_id
                    )

                elif message_type == "get_activity_stats":
                    # 获取活动统计信息
                    stats = manager.get_all_activity_stats()
                    await manager.send_personal_message(
                        json.dumps({
                            "type": "activity_stats",
                            "data": stats
                        }),
                        connection_id
                    )

                else:
                    # 未知消息类型
                    await manager.send_personal_message(
                        json.dumps({
                            "type": "error",
                            "message": f"未知消息类型: {message_type}"
                        }),
                        connection_id
                    )

            except json.JSONDecodeError:
                await manager.send_personal_message(
                    json.dumps({
                        "type": "error",
                        "message": "消息格式错误，请发送有效的JSON"
                    }),
                    connection_id
                )

    except WebSocketDisconnect:
        manager.disconnect(connection_id)
    except Exception as e:
        # 处理其他异常
        manager.disconnect(connection_id)
