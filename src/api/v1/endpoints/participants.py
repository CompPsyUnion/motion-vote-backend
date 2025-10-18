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
    status: Optional[str] = Query(
        default=None, description="参与状态筛选 (all|checked_in|not_checked_in)"),
    search: Optional[str] = Query(
        default=None, description="搜索关键词 - 支持姓名、编号、手机号模糊匹配"),
    name: Optional[str] = Query(default=None, description="姓名模糊匹配"),
    code: Optional[str] = Query(default=None, description="参与者编号模糊匹配"),
    phone: Optional[str] = Query(default=None, description="手机号模糊匹配"),
    note: Optional[str] = Query(default=None, description="备注信息模糊匹配"),
    checked_in: Optional[bool] = Query(default=None, description="入场状态筛选"),
    sort_by: Optional[str] = Query(
        default="created_at", description="排序字段 (created_at|name|code|checked_in_at)"),
    sort_order: Optional[str] = Query(
        default="desc", description="排序方向 (asc|desc)"),
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
    file: UploadFile = File(..., description="Excel或CSV文件"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """通过Excel或CSV文件批量导入参与者
    
    支持的文件格式：
    - Excel: .xlsx, .xls
    - CSV: .csv (支持UTF-8、GBK等编码)
    
    支持的文件布局：
    1. **导入模板格式**（简化）：
       - 列：姓名、手机号、备注
       - 适合从零开始创建参与者名单
    
    2. **导出文件格式**（完整）：
       - 列：编号、姓名、手机号、备注、是否入场、入场时间、创建时间
       - 支持直接编辑导出的文件并重新导入
       - 导入时会自动忽略编号、入场状态等字段，重新生成
    
    智能列识别：
    - 系统会自动识别标题行中的"姓名"、"手机号"、"备注"列
    - 支持中英文列名
    - 你可以直接使用导出的文件，在末尾添加新参与者后重新导入
    
    文件格式要求：
    - 第一行必须是标题行
    - 姓名列必填，其他列可选
    - CSV文件建议使用UTF-8编码保存
    
    示例 - 简化格式：
    ```
    姓名,手机号,备注
    张三,13800138000,VIP会员
    李四,13900139000,
    王五,,普通参与者
    ```
    
    示例 - 完整格式（导出文件）：
    ```
    编号,姓名,手机号,备注,是否入场,入场时间,创建时间
    0001,张三,13800138000,VIP会员,是,2025-01-01 10:00:00,2025-01-01 09:00:00
    0002,李四,13900139000,,否,,2025-01-01 09:00:00
    0003,王五,,新增参与者,否,,
    ```
    注：导入时编号、入场状态等会被自动重新生成，你只需关注姓名、手机号、备注即可。
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="未提供文件")
    
    filename_lower = file.filename.lower()
    if not filename_lower.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(
            status_code=400, 
            detail="不支持的文件格式，请上传Excel文件(.xlsx, .xls)或CSV文件(.csv)"
        )

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
        headers={
            "Content-Disposition": f"attachment; filename=participants_{activity_id}.csv"}
    )
