from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, String, Text
from src.core.database import Base


class SiteInfo(Base):
    """站点信息表"""
    __tablename__ = "site_info"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False, default="Motion Vote")
    description = Column(Text, nullable=True)
    logo = Column(String, nullable=True)  # 标志URL
    icon = Column(String, nullable=True)  # 图标URL
    contact = Column(String, nullable=True)  # 联系方式链接
    icp = Column(String, nullable=True)  # ICP备案号
    footer_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(
        timezone.utc).replace(tzinfo=None))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
                        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
