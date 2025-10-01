"""参与者管理 API 端点

基于 OpenAPI 规范实现的参与者管理接口，包括：
- 参与者的CRUD操作
- 批量导入和导出
- 二维码和链接生成
- 参与者入场
"""

import io
from typing import Optional

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user, get_db
from src.models.user import User
from src.schemas.base import ApiResponse
from src.schemas.participant import (
    ParticipantCreate, ParticipantResponse, PaginatedParticipants,
    ParticipantBatchImportResult, ParticipantEnter
)
from src.services.participant_service import ParticipantService

router = APIRouter()


@router.get("/{activity_id}/participants", response_model=PaginatedParticipants)
async def get_participants(
    activity_id: str,
    page: int = Query(default=1, description="页码"),
    limit: int = Query(default=50, description="每页数量"),
    status: Optional[str] = Query(default=None, description="参与状态筛选", regex="^(all|checked_in|not_checked_in)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取活动的参与者列表"""
    service = ParticipantService(db)
    return service.get_participants_paginated(
        activity_id=activity_id,
        user_id=str(current_user.id),
        page=page,
        limit=limit,
        status=status
    )


@router.post("/{activity_id}/participants", response_model=ParticipantResponse, status_code=201)
async def create_participant(
    activity_id: str,
    participant_data: ParticipantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """手动添加单个参与者"""
    service = ParticipantService(db)
    return service.create_participant(
        activity_id=activity_id,
        participant_data=participant_data,
        user_id=str(current_user.id)
    )


@router.post("/{activity_id}/participants/batch", response_model=ParticipantBatchImportResult)
async def batch_import_participants(
    activity_id: str,
    file: UploadFile = File(..., description="Excel文件"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """通过Excel文件批量导入参与者"""
    if not file.filename or not file.filename.endswith(('.xlsx', '.xls')):
        raise ValueError("只支持Excel文件格式")
    
    service = ParticipantService(db)
    return service.batch_import_participants(
        activity_id=activity_id,
        file=file,
        user_id=str(current_user.id)
    )


@router.get("/{activity_id}/participants/export")
async def export_participants(
    activity_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """导出参与者列表为Excel文件"""
    service = ParticipantService(db)
    excel_data = service.export_participants(
        activity_id=activity_id,
        user_id=str(current_user.id)
    )
    
    return StreamingResponse(
        io.BytesIO(excel_data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=participants_{activity_id}.xlsx"}
    )



