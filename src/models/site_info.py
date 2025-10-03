from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, String, Text
from src.core.database import Base


class SiteInfo(Base):
    """站点信息表"""
    __tablename__ = "site_info"

    id = Column(String, primary_key=True, index=True, default="default")
    title = Column(String, nullable=False, default="Motion Vote")
    description = Column(Text, nullable=True)
    open_register = Column(Boolean, default=True)
    icon = Column(String, nullable=True)  # 图标URL
    contact = Column(String, nullable=True)  # 联系方式链接
    icp = Column(String, nullable=True)  # ICP备案号
    footer_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)
