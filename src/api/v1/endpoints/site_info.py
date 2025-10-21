from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.schemas.site_info import SiteInfoResponse, SiteInfoUpdate
from src.services.site_info_service import SiteInfoService

router = APIRouter()


@router.get("/info", response_model=SiteInfoResponse)
@router.get("/info/", response_model=SiteInfoResponse)
async def get_site_info(
    db: Session = Depends(get_db)
):
    """获取站点信息"""
    site_info_service = SiteInfoService(db)
    site_info = site_info_service.get_site_info()
    return SiteInfoResponse.model_validate(site_info)


@router.post("/info", response_model=SiteInfoResponse)
@router.post("/info/", response_model=SiteInfoResponse)
async def update_site_info(
    site_data: SiteInfoUpdate,
    db: Session = Depends(get_db)
):
    """更新站点信息"""
    site_info_service = SiteInfoService(db)
    site_info = site_info_service.update_site_info(site_data)
    return SiteInfoResponse.model_validate(site_info)
