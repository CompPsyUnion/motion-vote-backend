"""统计数据相关的 API 端点"""

import io
from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from src.api.dependencies import get_current_user, get_db
from src.models.user import User
from src.schemas.statistics import ExportType
from src.services.statistics_service import StatisticsService

router = APIRouter()


@router.get("/{activity_id}/dashboard", response_model=dict)
async def get_dashboard_data(
    activity_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取实时数据看板

    返回活动的实时统计数据，包括参与人数、投票情况、辩题统计等信息
    """
    service = StatisticsService(db)
    dashboard_data = service.get_dashboard_data(
        activity_id=activity_id,
        user=current_user
    )

    return {
        "success": True,
        "message": "获取成功",
        "data": dashboard_data.model_dump(by_alias=True)
    }


@router.get("/{activity_id}/report", response_model=dict)
async def get_activity_report(
    activity_id: str,
    format: str = Query("json", description="报告格式",
                        regex="^(json|pdf|excel)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取活动报告

    返回活动的完整数据报告，包括活动摘要、辩题结果、投票时间线等信息
    """
    service = StatisticsService(db)

    if format == "json":
        report_data = service.get_activity_report(
            activity_id=activity_id,
            user=current_user
        )

        return {
            "success": True,
            "message": "获取成功",
            "data": report_data.model_dump(by_alias=True)
        }
    elif format == "pdf":
        # 生成PDF报告
        pdf_content = service.generate_pdf_report(activity_id, current_user)

        return StreamingResponse(
            io.BytesIO(pdf_content),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=activity_report_{activity_id}.pdf"
            }
        )
    elif format == "excel":
        # 生成Excel报告
        excel_content = service.generate_excel_report(
            activity_id, current_user)

        return StreamingResponse(
            io.BytesIO(excel_content),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename=activity_report_{activity_id}.xlsx"
            }
        )
    else:
        return {
            "success": False,
            "message": f"暂不支持{format}格式导出",
            "data": None
        }


@router.get("/{activity_id}/export")
async def export_data(
    activity_id: str,
    type: ExportType = Query(ExportType.ALL, description="导出数据类型"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """导出原始数据

    导出活动的原始投票数据为CSV格式
    """
    service = StatisticsService(db)
    csv_data = service.export_data(
        activity_id=activity_id,
        user=current_user,
        export_type=type
    )

    # 生成文件名
    type_names = {
        ExportType.VOTES: "votes",
        ExportType.CHANGES: "changes",
        ExportType.TIMELINE: "timeline",
        ExportType.ALL: "all"
    }
    filename = f"activity_{activity_id}_{type_names.get(type, 'data')}.csv"

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )
