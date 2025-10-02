"""参与者管理 API 端点

基于 OpenAPI 规范实现的参与者管理接口，包括：
- 参与者的CRUD操作
- 批量导入和导出
- 二维码和链接生成
- 参与者入场
"""

import io
from typing import Optional, Union

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from src.api.dependencies import get_current_user, get_db
from src.models.user import User
from src.schemas.participant import (PaginatedParticipants,
                                     ParticipantBatchImportResult,
                                     ParticipantCreate, ParticipantResponse)
from src.services.participant_service import ParticipantService

router = APIRouter()


@router.get("/{activity_id}/participants", response_model=PaginatedParticipants)
async def get_participants(
    activity_id: str,
    page: Union[int, str, None] = Query(default=1, description="页码"),
    limit: Union[int, str, None] = Query(default=50, description="每页数量"),
    status: Optional[str] = Query(default=None, description="参与状态筛选 (all|checked_in|not_checked_in)"),
    search: Optional[str] = Query(default=None, description="搜索关键词 - 支持姓名、编号、手机号模糊匹配"),
    name: Optional[str] = Query(default=None, description="姓名模糊匹配"),
    code: Optional[str] = Query(default=None, description="参与者编号模糊匹配"),
    phone: Optional[str] = Query(default=None, description="手机号模糊匹配"),
    note: Optional[str] = Query(default=None, description="备注信息模糊匹配"),
    checked_in: Optional[bool] = Query(default=None, description="入场状态筛选"),
    sort_by: Optional[str] = Query(default="created_at", description="排序字段 (created_at|name|code|checked_in_at)"),
    sort_order: Optional[str] = Query(default="desc", description="排序方向 (asc|desc)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取活动的参与者列表
    
    支持多种筛选和搜索方式：
    - search: 全文搜索(姓名、编号、手机号)
    - name: 姓名模糊匹配
    - code: 编号模糊匹配
    - phone: 手机号模糊匹配
    - note: 备注模糊匹配
    - checked_in: 入场状态筛选
    - sort_by/sort_order: 自定义排序
    """
    service = ParticipantService(db)
    
    # 处理可能为 None 或空字符串的参数，提供默认值
    def parse_int_param(value: Union[int, str, None], default: int) -> int:
        if value is None or value == "" or value == "null":
            return default
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                return default
        return value
    
    actual_page = parse_int_param(page, 1)
    actual_limit = parse_int_param(limit, 50)
    
    return service.get_participants_paginated(
        activity_id=activity_id,
        user_id=str(current_user.id),
        page=actual_page,
        limit=actual_limit,
        status=status,
        search=search,
        name=name,
        code=code,
        phone=phone,
        note=note,
        checked_in=checked_in,
        sort_by=sort_by,
        sort_order=sort_order
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
        raise HTTPException(status_code=400, detail="只支持Excel文件格式(.xlsx, .xls)")
    
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
    """导出参与者列表为CSV文件"""
    service = ParticipantService(db)
    csv_data = service.export_participants(
        activity_id=activity_id,
        user_id=str(current_user.id)
    )
    
    return StreamingResponse(
        io.BytesIO(csv_data),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=participants_{activity_id}.csv"}
    )



