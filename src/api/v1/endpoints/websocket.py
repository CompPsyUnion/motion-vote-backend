from fastapi import APIRouter, WebSocket
from src.core.websocket import websocket_endpoint

router = APIRouter()


@router.websocket("/live/{activity_id}")
async def websocket_live(websocket: WebSocket, activity_id: str):
    """活动实时数据 WebSocket 连接"""
    await websocket_endpoint(websocket, activity_id)
