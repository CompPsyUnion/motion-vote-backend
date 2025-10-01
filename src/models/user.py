import uuid

from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.core.database import Base
from src.schemas.user import UserRole


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True,
                default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=True)
    avatar = Column(String(500), nullable=True)
    role = Column(SQLEnum(UserRole),
                  default=UserRole.organizer, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(), onupdate=func.now())

    # 关系
    owned_activities = relationship("Activity", back_populates="owner")
    collaborations = relationship("Collaborator", back_populates="user")
