"""
Socket.IO Manager for real-time screen updates
大屏实时数据推送管理器
"""
from datetime import datetime
import logging
from typing import Any, Dict, Optional
import traceback

import socketio
from src.config import settings
from src.utils.logger import socketio_logger

# 创建 Socket.IO 服务器实例
# 允许所有源访问以便于开发和部署
socketio_logger.info(f"Settings CORS origins: {settings.cors_origins}")
socketio_logger.info("Initializing Socket.IO server with CORS: *")

# 配置 Socket.IO 和 Engine.IO 的日志
sio_internal_logger = logging.getLogger('socketio.server')
sio_internal_logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'))
sio_internal_logger.addHandler(handler)

engineio_internal_logger = logging.getLogger('engineio.server')
engineio_internal_logger.setLevel(logging.DEBUG)
engineio_internal_logger.addHandler(handler)

sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',  # 允许所有源访问
    cors_credentials=False,     # 不需要凭证
    logger=True,  # 启用内部日志
    engineio_logger=True,  # 启用 Engine.IO 日志
)

socketio_logger.info("Socket.IO server initialized successfully")


class ScreenSocketManager:
    """大屏 Socket.IO 连接管理器"""

    def __init__(self):
        # 存储房间信息 {activity_id: {session_id: user_info}}
        self.rooms: Dict[str, Dict[str, Dict[str, Any]]] = {}
        # 存储会话到活动的映射 {session_id: activity_id}
        self.session_activities: Dict[str, str] = {}

    def add_connection(self, session_id: str, activity_id: str, user_info: Optional[Dict] = None):
        """添加连接到房间"""
        if activity_id not in self.rooms:
            self.rooms[activity_id] = {}

        self.rooms[activity_id][session_id] = user_info or {}
        self.session_activities[session_id] = activity_id

    def remove_connection(self, session_id: str):
        """移除连接"""
        if session_id in self.session_activities:
            activity_id = self.session_activities[session_id]

            if activity_id in self.rooms and session_id in self.rooms[activity_id]:
                del self.rooms[activity_id][session_id]

                # 如果房间为空，删除房间
                if not self.rooms[activity_id]:
                    del self.rooms[activity_id]

            del self.session_activities[session_id]

    def get_room_info(self, activity_id: str) -> Dict[str, Any]:
        """获取房间信息"""
        if activity_id not in self.rooms:
            return {"activity_id": activity_id, "connections": 0, "users": []}

        return {
            "activity_id": activity_id,
            "connections": len(self.rooms[activity_id]),
            "users": list(self.rooms[activity_id].values())
        }

    def get_activity_id(self, session_id: str) -> Optional[str]:
        """根据会话ID获取活动ID"""
        return self.session_activities.get(session_id)


# 全局管理器实例
screen_manager = ScreenSocketManager()


# Socket.IO 事件处理器
@sio.event
async def connect(sid, environ, auth):
    """客户端连接事件"""
    try:
        origin = environ.get('HTTP_ORIGIN', 'unknown')
        user_agent = environ.get('HTTP_USER_AGENT', 'unknown')
        host = environ.get('HTTP_HOST', 'unknown')
        path = environ.get('PATH_INFO', 'unknown')
        method = environ.get('REQUEST_METHOD', 'unknown')

        socketio_logger.info("=" * 80)
        socketio_logger.info("🔗 Socket.IO Connection Attempt")
        socketio_logger.info(f"   Session ID: {sid}")
        socketio_logger.info(f"   Origin: {origin}")
        socketio_logger.info(f"   Host: {host}")
        socketio_logger.info(f"   Path: {path}")
        socketio_logger.info(f"   Method: {method}")
        socketio_logger.info(f"   User-Agent: {user_agent[:100]}")
        socketio_logger.info(f"   Auth: {auth}")
        socketio_logger.info("=" * 80)

        await sio.emit('connection_status', {
            'status': 'connected',
            'session_id': sid,
            'timestamp': datetime.now().isoformat()
        }, room=sid)

        socketio_logger.info(
            f"✅ Client {sid} connected successfully from {origin}")
    except Exception as e:
        socketio_logger.error(f"❌ Error in connect handler: {e}")
        socketio_logger.error(traceback.format_exc())


@sio.event
async def disconnect(sid):
    """客户端断开连接事件"""
    try:
        socketio_logger.info(f"🔌 Client disconnected: {sid}")
        screen_manager.remove_connection(sid)
    except Exception as e:
        socketio_logger.error(f"❌ Error in disconnect handler: {e}")
        socketio_logger.error(traceback.format_exc())


@sio.event
async def connect_error(sid, data):
    """连接错误处理"""
    socketio_logger.error(f"❌ Connection error for {sid}: {data}")
    socketio_logger.error(f"   Error data: {data}")


@sio.event
async def join_screen(sid, data):
    """加入大屏房间"""
    try:
        socketio_logger.info(f"📥 Received join_screen request from {sid}")
        socketio_logger.debug(f"   Data: {data}")

        activity_id = data.get('activity_id')
        if not activity_id:
            socketio_logger.warning(
                f"⚠️ Missing activity_id in join_screen request from {sid}")
            await sio.emit('error', {
                'message': 'activity_id is required'
            }, room=sid)
            return

        # 加入房间
        await sio.enter_room(sid, f"screen_{activity_id}")
        screen_manager.add_connection(sid, activity_id, data.get('user_info'))

        # 发送加入成功消息
        await sio.emit('joined_screen', {
            'activity_id': activity_id,
            'session_id': sid,
            'timestamp': datetime.now().isoformat()
        }, room=sid)

        socketio_logger.info(
            f"✅ Client {sid} joined screen room: {activity_id}")

    except Exception as e:
        socketio_logger.error(f"❌ Error in join_screen: {e}")
        socketio_logger.error(traceback.format_exc())
        await sio.emit('error', {
            'message': str(e)
        }, room=sid)


@sio.event
async def leave_screen(sid, data):
    """离开大屏房间"""
    try:
        socketio_logger.info(f"📤 Received leave_screen request from {sid}")
        activity_id = screen_manager.get_activity_id(sid)
        if activity_id:
            await sio.leave_room(sid, f"screen_{activity_id}")
            screen_manager.remove_connection(sid)

            await sio.emit('left_screen', {
                'activity_id': activity_id,
                'session_id': sid,
                'timestamp': datetime.now().isoformat()
            }, room=sid)

            socketio_logger.info(
                f"✅ Client {sid} left screen room: {activity_id}")

    except Exception as e:
        socketio_logger.error(f"❌ Error in leave_screen: {e}")
        socketio_logger.error(traceback.format_exc())
        await sio.emit('error', {
            'message': str(e)
        }, room=sid)


@sio.event
async def request_screen_data(sid, data):
    """请求大屏数据"""
    try:
        socketio_logger.info(f"📊 Received request_screen_data from {sid}")
        socketio_logger.debug(f"   Data: {data}")

        activity_id = data.get('activity_id')
        if not activity_id:
            await sio.emit('error', {
                'message': 'activity_id is required'
            }, room=sid)
            return

        # 这里需要从数据库获取实际数据
        # 暂时返回示例响应
        await sio.emit('screen_data', {
            'activity_id': activity_id,
            'timestamp': datetime.now().isoformat(),
            'message': 'Please implement database query in screen endpoint'
        }, room=sid)

        socketio_logger.info(
            f"✅ Sent screen_data to {sid} for activity {activity_id}")

    except Exception as e:
        socketio_logger.error(f"❌ Error in request_screen_data: {e}")
        socketio_logger.error(traceback.format_exc())
        await sio.emit('error', {
            'message': str(e)
        }, room=sid)


# 工具函数：向特定活动的所有大屏广播数据
async def broadcast_to_screen(activity_id: str, event: str, data: Dict[str, Any]):
    """向指定活动的所有大屏客户端广播数据"""
    try:
        room = f"screen_{activity_id}"
        await sio.emit(event, data, room=room)
        socketio_logger.info(f"📢 Broadcasted {event} to room {room}")
    except Exception as e:
        socketio_logger.error(f"❌ Error broadcasting to screen: {e}")
        socketio_logger.error(traceback.format_exc())


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
