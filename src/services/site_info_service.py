from sqlalchemy.orm import Session
from src.models.site_info import SiteInfo
from src.schemas.site_info import SiteInfoUpdate


class SiteInfoService:
    """站点信息服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.default_id = "default"
    
    def get_site_info(self) -> SiteInfo:
        """获取站点信息"""
        site_info = self.db.query(SiteInfo).filter(
            SiteInfo.id == self.default_id
        ).first()
        
        if not site_info:
            # 创建默认站点信息
            site_info = SiteInfo(
                id=self.default_id,
                title="Motion Vote",
                description="辩论活动实时投票互动系统",
                open_register=True
            )
            self.db.add(site_info)
            self.db.commit()
            self.db.refresh(site_info)
        
        return site_info
    
    def update_site_info(self, site_data: SiteInfoUpdate) -> SiteInfo:
        """更新站点信息"""
        site_info = self.get_site_info()
        
        # 更新字段
        update_data = site_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(site_info, field, value)
        
        self.db.commit()
        self.db.refresh(site_info)
        
        return site_info