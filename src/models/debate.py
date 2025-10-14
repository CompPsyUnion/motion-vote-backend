import uuid

from sqlalchemy import Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.core.database import Base
from src.schemas.debate import DebateStatus


class Debate(Base):
    __tablename__ = "debates"

    id = Column(String(36), primary_key=True,
                default=lambda: str(uuid.uuid4()))
    title = Column(String(300), nullable=False)
    pro_description = Column(Text, nullable=False)
    con_description = Column(Text, nullable=False)
    background = Column(Text, nullable=True)
    status = Column(SQLEnum(DebateStatus),
                    default=DebateStatus.pending, nullable=False)
    estimated_duration = Column(Integer, nullable=True)
    order = Column(Integer, nullable=False, default=0)

    # 辩题时间跟踪
    started_at = Column(DateTime(timezone=True),
                        nullable=True, comment="辩题开始时间")
    ended_at = Column(DateTime(timezone=True), nullable=True, comment="辩题结束时间")

    # 外键
    activity_id = Column(String(36), ForeignKey(
        "activities.id"), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(), onupdate=func.now())

    # 关系
    activity = relationship("Activity", back_populates="debates",
                            foreign_keys=[activity_id])
    votes = relationship("Vote", back_populates="debate",
                         cascade="all, delete-orphan")
