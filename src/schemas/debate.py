from datetime import datetime
from enum import Enum
from typing import Optional
import json

from pydantic import BaseModel, Field, field_validator
from src.schemas.vote import VoteStats


class DebateStatus(str, Enum):
    pending = "pending"
    ongoing = "ongoing"
    final_vote = "final_vote"
    ended = "ended"


class BellTimingType(str, Enum):
    start = "start"
    warning = "warning"
    end = "end"


class DebateSide(BaseModel):
    name: str = Field(..., description="辩手名称")
    duration: int = Field(..., description="时长（秒）")


class BellTiming(BaseModel):
    time: int = Field(..., description="时间点（秒）")
    type: BellTimingType = Field(..., description="铃声类型")


class DebateStage(BaseModel):
    stage_name: str = Field(..., alias="stageName", description="阶段名称")
    is_dual_side: bool = Field(..., alias="isDualSide", description="是否双边辩论")
    sides: list[DebateSide] = Field(..., description="辩手配置")
    bell_timings: list[BellTiming] = Field(...,
                                           alias="bellTimings", description="铃声时间配置")
    hide_timer: Optional[bool] = Field(
        False, alias="hideTimer", description="是否隐藏计时器")

    model_config = {"populate_by_name": True}


class DebateBase(BaseModel):
    title: str = Field(..., description="辩题标题")
    pro_description: str = Field(...,
                                 alias="proDescription", description="正方观点描述")
    con_description: str = Field(...,
                                 alias="conDescription", description="反方观点描述")
    background: Optional[str] = Field(None, description="辩题背景介绍")
    estimated_duration: Optional[int] = Field(
        None, alias="estimatedDuration", description="预计辩论时长（分钟）")
    background_image_url: Optional[str] = Field(
        None, alias="backgroundImageUrl", description="辩题背景图")

    model_config = {"populate_by_name": True}


class DebateCreate(DebateBase):
    pass


class DebateUpdate(BaseModel):
    title: Optional[str] = Field(None, description="辩题标题")
    pro_description: Optional[str] = Field(
        None, alias="proDescription", description="正方观点描述")
    con_description: Optional[str] = Field(
        None, alias="conDescription", description="反方观点描述")
    background: Optional[str] = Field(None, description="辩题背景介绍")
    estimated_duration: Optional[int] = Field(
        None, alias="estimatedDuration", description="预计辩论时长（分钟）")
    background_image_url: Optional[str] = Field(
        None, alias="backgroundImageUrl", description="辩题背景图")

    model_config = {"populate_by_name": True}


class DebateStatusUpdate(BaseModel):
    status: DebateStatus = Field(..., description="辩题状态")


class DebateOrderItem(BaseModel):
    id: str = Field(..., description="辩题ID")
    order: int = Field(..., description="新的排序号")


class DebateReorder(BaseModel):
    debates: list[DebateOrderItem] = Field(..., description="辩题顺序调整列表")


class CurrentDebateUpdate(BaseModel):
    debate_id: str = Field(..., alias="debateId", description="当前辩题ID")

    model_config = {"populate_by_name": True}


class DebateResponse(DebateBase):
    id: str = Field(..., description="辩题ID")
    activity_id: str = Field(..., alias="activityId", description="活动ID")
    status: DebateStatus = Field(..., description="辩题状态")
    order: int = Field(..., description="排序号")
    created_at: datetime = Field(..., alias="createdAt", description="创建时间")
    updated_at: datetime = Field(..., alias="updatedAt", description="更新时间")
    stages: list[DebateStage] = Field(
        default_factory=list, description="辩论阶段列表")

    @field_validator('stages', mode='before')
    @classmethod
    def parse_stages(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return []
        return v

    model_config = {"from_attributes": True, "populate_by_name": True}


class DebateDetailResponse(DebateResponse):
    vote_stats: VoteStats = Field(
        default_factory=lambda: VoteStats(debateId=None, winner=None, lockedAt=None), description="投票统计")
