import uuid

from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.core.database import Base
from src.schemas.vote import VotePosition


class Participant(Base):
    __tablename__ = "participants"

    id = Column(String(36), primary_key=True,
                default=lambda: str(uuid.uuid4()))
    code = Column(String(50), nullable=False)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=True)
    note = Column(String(500), nullable=True)
    checked_in = Column(Boolean, default=False, nullable=False)
    checked_in_at = Column(DateTime(timezone=True), nullable=True)
    device_fingerprint = Column(String(500), nullable=True)
    session_token = Column(String(500), nullable=True)

    # 外键
    activity_id = Column(String(36), ForeignKey(
        "activities.id"), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    activity = relationship("Activity", back_populates="participants")
    votes = relationship("Vote", back_populates="participant",
                         cascade="all, delete-orphan")


class Vote(Base):
    __tablename__ = "votes"

    id = Column(String(36), primary_key=True,
                default=lambda: str(uuid.uuid4()))
    position = Column(SQLEnum(VotePosition), nullable=False)
    change_count = Column(Integer, default=0, nullable=False)
    is_final = Column(Boolean, default=False, nullable=False)

    # 外键
    participant_id = Column(String(36), ForeignKey(
        "participants.id"), nullable=False)
    debate_id = Column(String(36), ForeignKey("debates.id"), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(), onupdate=func.now())

    # 关系
    participant = relationship("Participant", back_populates="votes")
    debate = relationship("Debate", back_populates="votes")


class VoteHistory(Base):
    __tablename__ = "vote_history"

    id = Column(String(36), primary_key=True,
                default=lambda: str(uuid.uuid4()))
    old_position = Column(SQLEnum(VotePosition), nullable=True)
    new_position = Column(SQLEnum(VotePosition), nullable=False)

    # 外键
    vote_id = Column(String(36), ForeignKey("votes.id"), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    vote = relationship("Vote")
