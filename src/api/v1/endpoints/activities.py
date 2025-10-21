"""活动管理 API 端点

基于 OpenAPI 规范实现的活动管理接口，包括：
- 活动的CRUD操作
- 协作者管理
- 权限控制
"""

import io
from typing import List, Optional, Union

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from src.api.dependencies import get_current_user, get_db
from src.models.user import User
from src.schemas.activity import (ActivityCreate, ActivityDetail,
                                  ActivityResponse, ActivityUpdate,
                                  CollaboratorInvite, CollaboratorResponse,
                                  CollaboratorUpdate, PaginatedActivities)
from src.schemas.base import ApiResponse
from src.schemas.debate import CurrentDebateUpdate, DebateCreate
from src.schemas.participant import (PaginatedParticipants,
                                     ParticipantBatchImportResult,
                                     ParticipantCreate, ParticipantResponse)
from src.services.activity_service import ActivityService
from src.services.debate_service import DebateService
from src.services.participant_service import ParticipantService

router = APIRouter()


router = APIRouter()


@router.get("/", response_model=PaginatedActivities)
async def get_activities(
    page: int = Query(default=1, ge=1, description="页码"),
    limit: int = Query(default=20, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(
        default=None, description="活动状态筛选 (upcoming|ongoing|ended)"),
    role: Optional[str] = Query(
        default=None, description="用户角色筛选 (owner|collaborator)"),
    search: Optional[str] = Query(
        default=None, description="搜索关键词 - 支持活动名称、描述、地址模糊匹配"),
    name: Optional[str] = Query(default=None, description="活动名称模糊匹配"),
    location: Optional[str] = Query(default=None, description="活动地址模糊匹配"),
    tags: Optional[str] = Query(default=None, description="标签搜索，多个标签用逗号分隔"),
    date_from: Optional[str] = Query(
        default=None, description="开始时间筛选 (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(
        default=None, description="结束时间筛选 (YYYY-MM-DD)"),
    sort_by: Optional[str] = Query(
        default="created_at", description="排序字段 (created_at|name|start_time)"),
    sort_order: Optional[str] = Query(
        default="desc", description="排序方向 (asc|desc)"),
    db: Session = Depends(get_db)
):
    """获取用户创建和参与的活动列表

    支持多种筛选和搜索方式：
    - search: 全文搜索(名称、描述、地址)
    - name: 活动名称模糊匹配
    - location: 地址模糊匹配
    - tags: 标签搜索
    - date_from/date_to: 时间范围筛选
    - sort_by/sort_order: 自定义排序
    """
    service = ActivityService(db)
    # 构建增强的搜索参数
    enhanced_search = search
    if name or location or tags:
        search_parts = []
        if enhanced_search:
            search_parts.append(enhanced_search)
        if name:
            search_parts.append(name)
        if location:
            search_parts.append(location)
        if tags:
            search_parts.extend(tags.split(','))
        enhanced_search = ' '.join(search_parts)

    return service.get_activities_paginated(
        user_id=None,
        page=page,
        limit=limit,
        status=status,
        role=role,
        search=enhanced_search
    )


@router.post("/", response_model=ActivityResponse, status_code=201)
async def create_activity(
    activity_data: ActivityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建新的辩论活动"""
    service = ActivityService(db)
    return service.create_activity(activity_data, str(current_user.id))


@router.get("/{activity_id}", response_model=ActivityDetail)
async def get_activity_detail(
    activity_id: str,
    db: Session = Depends(get_db)
):
    """获取指定活动的详细信息"""
    service = ActivityService(db)
    return service.get_activity_detail(activity_id, None)


@router.put("/{activity_id}", response_model=ApiResponse)
async def update_activity(
    activity_id: str,
    activity_data: ActivityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新活动信息"""
    service = ActivityService(db)
    service.update_activity(activity_id, activity_data, str(current_user.id))
    return ApiResponse(
        message="Activity updated successfully"
    )


@router.delete("/{activity_id}", response_model=ApiResponse)
async def delete_activity(
    activity_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除指定活动"""
    service = ActivityService(db)
    service.delete_activity(activity_id, str(current_user.id))
    return ApiResponse(
        message="Activity deleted successfully"
    )


@router.get("/{activity_id}/collaborators", response_model=List[CollaboratorResponse])
async def get_collaborators(
    activity_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取活动的协作者列表"""
    service = ActivityService(db)
    return service.get_collaborators(activity_id, current_user)


@router.post("/{activity_id}/collaborators", response_model=ApiResponse, status_code=201)
async def invite_collaborator(
    activity_id: str,
    invite_data: CollaboratorInvite,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """邀请用户成为活动协作者"""
    service = ActivityService(db)
    service.invite_collaborator(activity_id, invite_data, current_user)
    return ApiResponse(
        message="Collaborator invited successfully"
    )


@router.put("/{activity_id}/collaborators/{collaborator_id}", response_model=ApiResponse)
async def update_collaborator_permissions(
    activity_id: str,
    collaborator_id: str,
    update_data: CollaboratorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新协作者的权限设置"""
    service = ActivityService(db)
    service.update_collaborator_permissions(
        activity_id, collaborator_id, update_data, current_user
    )
    return ApiResponse(
        message="Collaborator permissions updated successfully"
    )


@router.delete("/{activity_id}/collaborators/{collaborator_id}", response_model=ApiResponse)
async def remove_collaborator(
    activity_id: str,
    collaborator_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """从活动中移除协作者"""
    service = ActivityService(db)
    service.remove_collaborator(
        activity_id, collaborator_id, current_user)
    return ApiResponse(
        message="Collaborator removed successfully"
    )


# ==================== Debates 辩题管理 ====================

@router.get("/{activity_id}/debates")
async def get_activity_debates(
    activity_id: str,
    search: Optional[str] = Query(
        default=None, description="搜索关键词 - 支持辩题标题、描述模糊匹配"),
    status: Optional[str] = Query(
        default=None, description="辩题状态筛选 (draft|active|locked|archived)"),
    page: int = Query(default=1, ge=1, description="页码"),
    limit: int = Query(default=50, ge=1, le=100, description="每页数量"),
    sort_by: Optional[str] = Query(
        default="order", description="排序字段 (order|created_at|title)"),
    sort_order: Optional[str] = Query(
        default="asc", description="排序方向 (asc|desc)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取活动的辩题列表

    支持多种筛选和搜索方式：
    - search: 全文搜索(标题、描述)
    - status: 状态筛选
    - page/limit: 分页控制
    - sort_by/sort_order: 自定义排序
    """
    # 检查权限
    activity_service = ActivityService(db)
    activity_service.check_activity_permission(
        activity_id, "view", current_user
    )

    # 获取辩题列表
    debate_service = DebateService(db)
    data = debate_service.get_debates_paginated(
        activity_id=activity_id,
        page=page,
        limit=limit,
        search=search,
        status=status,
        sort_by=sort_by if sort_by is not None else "order",
        sort_order=sort_order if sort_order is not None else "asc"
    )

    return {
        "success": True,
        "message": "获取辩题列表成功",
        "data": data
    }


@router.post("/{activity_id}/debates", status_code=201)
async def create_activity_debate(
    activity_id: str,
    debate_data: DebateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """为活动创建新的辩题"""
    # 检查权限
    activity_service = ActivityService(db)
    activity_service.check_activity_permission(
        activity_id, "edit", current_user
    )

    # 创建辩题
    debate_service = DebateService(db)
    debate_response = debate_service.create_debate(activity_id, debate_data)

    return {
        "success": True,
        "message": "创建辩题成功",
        "data": debate_response
    }


# ==================== Participants 参与者管理 ====================
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


# ==================== Current Debate 当前辩题 ====================

@router.get("/{activity_id}/current-debate", response_model=ApiResponse)
async def get_current_debate(
    activity_id: str,
    db: Session = Depends(get_db)
):
    """获取活动的当前辩题"""
    debate_service = DebateService(db)
    debate_detail = debate_service.get_current_debate(activity_id)

    # 返回时将内部 Pydantic 模型序列化为使用别名的 dict
    return {
        "success": True,
        "message": "获取当前辩题成功",
        "data": debate_detail.model_dump(by_alias=True)
    }


@router.put("/{activity_id}/current-debate")
async def set_current_debate(
    activity_id: str,
    current_debate_data: CurrentDebateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """切换活动的当前辩题"""
    # 检查权限
    activity_service = ActivityService(db)
    try:
        activity_service.check_activity_permission(
            activity_id, "control", current_user
        )
    except Exception as e:
        print(f"Permission check failed: {e}")
        print(f"Activity ID: {activity_id}")
        print(f"User ID: {current_user.id}, Type: {type(current_user.id)}")
        raise

    # 设置当前辩题
    debate_service = DebateService(db)
    debate_service.set_current_debate(
        activity_id, current_debate_data.debate_id)

    return {
        "success": True,
        "message": "当前辩题切换成功"
    }
