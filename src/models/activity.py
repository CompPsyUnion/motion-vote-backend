import uuid

from sqlalchemy import JSON, Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.core.database import Base
from src.schemas.activity import (ActivityStatus, CollaboratorPermission,
                                  CollaboratorStatus)


class Activity(Base):
    __tablename__ = "activities"

    id = Column(String(36), primary_key=True,
                default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    location = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    cover_image = Column(String(500), nullable=True)
    status = Column(SQLEnum(ActivityStatus),
                    default=ActivityStatus.upcoming, nullable=False)
    expected_participants = Column(Integer, nullable=True)
    actual_participants = Column(Integer, default=0, nullable=False)
    tags = Column(JSON, default=list, nullable=False)
    settings = Column(JSON, nullable=False)

    # 外键
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    current_debate_id = Column(
        String(36), ForeignKey("debates.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(), onupdate=func.now())

    # 关系
    owner = relationship("User", back_populates="owned_activities")
    collaborators = relationship(
        "Collaborator", back_populates="activity", cascade="all, delete-orphan")
    debates = relationship(
        "Debate", back_populates="activity", cascade="all, delete-orphan",
        foreign_keys="[Debate.activity_id]")
    participants = relationship(
        "Participant", back_populates="activity", cascade="all, delete-orphan")
    current_debate = relationship("Debate", foreign_keys=[current_debate_id])


class Collaborator(Base):
    __tablename__ = "collaborators"

    id = Column(String(36), primary_key=True,
                default=lambda: str(uuid.uuid4()))
    permissions = Column(JSON, nullable=False)
    status = Column(SQLEnum(CollaboratorStatus),
                    default=CollaboratorStatus.pending, nullable=False)

    # 外键
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    activity_id = Column(String(36), ForeignKey(
        "activities.id"), nullable=False)

    invited_at = Column(DateTime(timezone=True), server_default=func.now())
    accepted_at = Column(DateTime(timezone=True), nullable=True)

    # 关系
    user = relationship("User", back_populates="collaborations")
    activity = relationship("Activity", back_populates="collaborators")
