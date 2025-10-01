from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class DebateStatus(str, Enum):
    pending = "pending"
    ongoing = "ongoing"
    final_vote = "final_vote"
    ended = "ended"


class DebateBase(BaseModel):
    title: str = Field(..., description="辩题标题")
    pro_description: str = Field(..., description="正方观点描述")
    con_description: str = Field(..., description="反方观点描述")
    background: Optional[str] = Field(None, description="辩题背景介绍")
    estimated_duration: Optional[int] = Field(None, description="预计辩论时长（分钟）")


class DebateCreate(DebateBase):
    pass


class DebateUpdate(BaseModel):
    title: Optional[str] = Field(None, description="辩题标题")
    pro_description: Optional[str] = Field(None, description="正方观点描述")
    con_description: Optional[str] = Field(None, description="反方观点描述")
    background: Optional[str] = Field(None, description="辩题背景介绍")
    estimated_duration: Optional[int] = Field(None, description="预计辩论时长（分钟）")


class DebateStatusUpdate(BaseModel):
    status: DebateStatus = Field(..., description="辩题状态")


class DebateOrderItem(BaseModel):
    id: str = Field(..., description="辩题ID")
    order: int = Field(..., description="新的排序号")


class DebateReorder(BaseModel):
    debates: list[DebateOrderItem] = Field(..., description="辩题顺序调整列表")


class CurrentDebateUpdate(BaseModel):
    debate_id: str = Field(..., description="当前辩题ID")


class DebateResponse(DebateBase):
    id: str = Field(..., description="辩题ID")
    activity_id: str = Field(..., description="活动ID")
    status: DebateStatus = Field(..., description="辩题状态")
    order: int = Field(..., description="排序号")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class VoteStats(BaseModel):
    total_votes: int = Field(default=0, description="总投票数")
    pro_votes: int = Field(default=0, description="正方票数")
    con_votes: int = Field(default=0, description="反方票数")
    abstain_votes: int = Field(default=0, description="弃权票数")
    pro_percentage: float = Field(default=0.0, description="正方得票率")
    con_percentage: float = Field(default=0.0, description="反方得票率")
    abstain_percentage: float = Field(default=0.0, description="弃权率")


class DebateDetailResponse(DebateResponse):
    vote_stats: VoteStats = Field(
        default_factory=VoteStats, description="投票统计")
