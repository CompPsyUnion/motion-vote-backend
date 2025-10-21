"""
WebSocket endpoints for screen real-time updates
大屏实时更新 WebSocket 端点
"""
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from src.core.websocket_manager import screen_manager
from src.utils.logger import websocket_logger

router = APIRouter()


@router.websocket("/{activity_id}")
@router.websocket("/{activity_id}/")
async def websocket_screen_endpoint(
    websocket: WebSocket,
    activity_id: str
):
    """
    大屏 WebSocket 连接端点

    Args:
        websocket: WebSocket 连接
        activity_id: 活动 ID
    """
    connection_id = None

    try:
        # 接受连接并自动加入房间
        connection_id = await screen_manager.connect(websocket, activity_id)

        websocket_logger.info(
            f"🔗 WebSocket connection established: {connection_id} for activity: {activity_id}")

        # 消息循环
        while True:
            try:
                # 接收客户端消息
                data = await websocket.receive_text()
                message = json.loads(data)

                message_type = message.get('type')

                websocket_logger.debug(
                    f"📨 Received message from {connection_id}: {message_type}")

                # 处理不同类型的消息
                if message_type == 'ping':
                    # 心跳检测
                    await screen_manager.send_personal_message(connection_id, {
                        'type': 'pong',
                        'timestamp': message.get('timestamp')
                    })

                elif message_type == 'join_screen':
                    # 重新加入或切换房间
                    new_activity_id = message.get('activity_id')
                    user_info = message.get('user_info')
                    if new_activity_id:
                        await screen_manager.join_room(connection_id, new_activity_id, user_info)

                elif message_type == 'leave_screen':
                    # 离开当前房间
                    await screen_manager.leave_room(connection_id)

                elif message_type == 'request_screen_data':
                    # 请求大屏数据
                    req_activity_id = message.get('activity_id')
                    if req_activity_id:
                        # 这里可以从数据库获取实际数据
                        # 暂时返回确认消息
                        await screen_manager.send_personal_message(connection_id, {
                            'type': 'screen_data',
                            'activity_id': req_activity_id,
                            'message': 'Data request received'
                        })

                else:
                    # 未知消息类型
                    await screen_manager.send_personal_message(connection_id, {
                        'type': 'error',
                        'message': f'Unknown message type: {message_type}'
                    })

            except json.JSONDecodeError:
                websocket_logger.error(f"❌ Invalid JSON from {connection_id}")
                await screen_manager.send_personal_message(connection_id, {
                    'type': 'error',
                    'message': 'Invalid JSON format'
                })
            except Exception as e:
                websocket_logger.error(
                    f"❌ Error processing message from {connection_id}: {e}")
                break

    except WebSocketDisconnect:
        websocket_logger.info(f"🔌 WebSocket disconnected: {connection_id}")
    except Exception as e:
        websocket_logger.error(f"❌ WebSocket error for {connection_id}: {e}")
    finally:
        # 清理连接
        if connection_id:
            screen_manager.disconnect(connection_id)


@router.websocket("")
@router.websocket("/")
async def websocket_screen_endpoint_without_activity(websocket: WebSocket):
    """
    大屏 WebSocket 连接端点（不指定活动）
    客户端需要发送 join_screen 消息来加入特定房间
    """
    connection_id = None

    try:
        # 接受连接但不自动加入房间
        connection_id = await screen_manager.connect(websocket)

        websocket_logger.info(
            f"🔗 WebSocket connection established: {connection_id} (no activity)")

        # 消息循环
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)

                message_type = message.get('type')

                if message_type == 'ping':
                    await screen_manager.send_personal_message(connection_id, {
                        'type': 'pong',
                        'timestamp': message.get('timestamp')
                    })

                elif message_type == 'join_screen':
                    activity_id = message.get('activity_id')
                    user_info = message.get('user_info')
                    if activity_id:
                        await screen_manager.join_room(connection_id, activity_id, user_info)
                    else:
                        await screen_manager.send_personal_message(connection_id, {
                            'type': 'error',
                            'message': 'activity_id is required'
                        })

                elif message_type == 'leave_screen':
                    await screen_manager.leave_room(connection_id)

                else:
                    await screen_manager.send_personal_message(connection_id, {
                        'type': 'error',
                        'message': f'Unknown message type: {message_type}'
                    })

            except json.JSONDecodeError:
                websocket_logger.error(f"❌ Invalid JSON from {connection_id}")
            except Exception as e:
                websocket_logger.error(f"❌ Error processing message: {e}")
                break

    except WebSocketDisconnect:
        websocket_logger.info(f"🔌 WebSocket disconnected: {connection_id}")
    except Exception as e:
        websocket_logger.error(f"❌ WebSocket error: {e}")
    finally:
        if connection_id:
            screen_manager.disconnect(connection_id)
