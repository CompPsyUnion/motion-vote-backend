"""Screen display schemas"""
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from src.schemas.activity import ActivityResponse
from src.schemas.debate import DebateResponse
from src.schemas.vote import VoteStats


class DisplayType(str, Enum):
    """大屏显示类型"""
    current_debate = "current_debate"
    pro_only = "pro_only"
    con_only = "con_only"
    both_sides = "both_sides"


class ScreenControlAction(str, Enum):
    """大屏控制动作"""
    switch_debate = "switch_debate"
    toggle_data = "toggle_data"
    show_cover = "show_cover"
    toggle_timer = "toggle_timer"
    start_timer = "start_timer"
    pause_timer = "pause_timer"
    next_session = "next_session"
    past_session = "past_session"
    start_debate = "start_debate"
    end_debate = "end_debate"


class ScreenDisplayData(BaseModel):
    """大屏显示数据"""
    activity: ActivityResponse = Field(..., description="活动信息")
    currentDebate: Optional[DebateResponse] = Field(
        None, description="当前辩题", alias="current_debate"
    )
    showData: bool = Field(
        default=True, description="是否显示投票数据", alias="show_data"
    )
    voteStats: Optional[VoteStats] = Field(
        None, description="投票结果", alias="vote_results"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now, description="数据时间戳"
    )

    class Config:
        populate_by_name = True
        from_attributes = True


class ScreenControlRequest(BaseModel):
    """大屏控制请求"""
    action: ScreenControlAction = Field(..., description="控制动作")
    debateId: Optional[str] = Field(
        None, description="辩题ID（switch_debate时必需）", alias="debate_id"
    )

    class Config:
        populate_by_name = True
