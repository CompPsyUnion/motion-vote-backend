"""统计数据相关的 Pydantic 模型"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ActivityType(str, Enum):
    """活动类型"""
    PARTICIPANT_JOIN = "participant_join"
    VOTE_CAST = "vote_cast"
    VOTE_CHANGE = "vote_change"
    DEBATE_SWITCH = "debate_switch"


class RecentActivity(BaseModel):
    """最近活动"""
    type: ActivityType = Field(..., description="活动类型")
    timestamp: datetime = Field(..., description="时间戳")
    description: str = Field(..., description="活动描述")

    class Config:
        from_attributes = True


class RealTimeStats(BaseModel):
    """实时统计数据"""
    total_participants: int = Field(...,
                                    alias="totalParticipants", description="总参与人数")
    checked_in_participants: int = Field(...,
                                         alias="checkedInParticipants", description="已入场人数")
    online_participants: int = Field(...,
                                     alias="onlineParticipants", description="在线人数")
    total_votes: int = Field(..., alias="totalVotes", description="总投票数")
    vote_rate: float = Field(..., alias="voteRate", description="投票率")

    class Config:
        populate_by_name = True


class VoteResults(BaseModel):
    """投票结果"""
    pro_votes: int = Field(..., alias="proVotes", description="正方票数")
    con_votes: int = Field(..., alias="conVotes", description="反方票数")
    abstain_votes: int = Field(..., alias="abstainVotes", description="弃权票数")
    total_votes: int = Field(..., alias="totalVotes", description="总票数")

    class Config:
        populate_by_name = True


class DebateStats(BaseModel):
    """辩题统计数据"""
    debate_id: str = Field(..., alias="debateId", description="辩题ID")
    debate_title: str = Field(..., alias="debateTitle", description="辩题标题")
    vote_results: VoteResults = Field(...,
                                      alias="voteResults", description="投票结果")
    vote_rate: float = Field(..., alias="voteRate", description="投票率")

    class Config:
        populate_by_name = True


class DashboardData(BaseModel):
    """实时数据看板"""
    activity_id: str = Field(..., alias="activityId", description="活动ID")
    activity_name: str = Field(..., alias="activityName", description="活动名称")
    activity_status: str = Field(...,
                                 alias="activityStatus", description="活动状态")
    current_debate: Optional[str] = Field(
        None, alias="currentDebate", description="当前辩题")
    real_time_stats: RealTimeStats = Field(...,
                                           alias="realTimeStats", description="实时统计数据")
    debate_stats: List[DebateStats] = Field(...,
                                            alias="debateStats", description="辩题统计")
    recent_activity: List[RecentActivity] = Field(
        ..., alias="recentActivity", description="最近活动")

    class Config:
        populate_by_name = True


class TimelinePoint(BaseModel):
    """时间线数据点"""
    timestamp: datetime = Field(..., description="时间点")
    pro_votes: int = Field(..., alias="proVotes", description="正方票数")
    con_votes: int = Field(..., alias="conVotes", description="反方票数")
    abstain_votes: int = Field(..., alias="abstainVotes", description="弃权票数")

    class Config:
        populate_by_name = True


class DebateResult(BaseModel):
    """辩题结果"""
    debate_id: str = Field(..., alias="debateId", description="辩题ID")
    debate_title: str = Field(..., alias="debateTitle", description="辩题标题")
    debate_order: int = Field(..., alias="debateOrder", description="辩题顺序")
    results: VoteResults = Field(..., description="投票结果")
    timeline: List[TimelinePoint] = Field(..., description="投票时间线")
    duration: int = Field(..., description="辩题持续时间（分钟）")

    class Config:
        populate_by_name = True


class ActivitySummary(BaseModel):
    """活动摘要"""
    total_participants: int = Field(...,
                                    alias="totalParticipants", description="总参与人数")
    total_votes: int = Field(..., alias="totalVotes", description="总投票数")
    total_debates: int = Field(..., alias="totalDebates", description="辩题总数")
    average_vote_rate: float = Field(...,
                                     alias="averageVoteRate", description="平均投票率")
    duration: int = Field(..., description="活动时长（分钟）")

    class Config:
        populate_by_name = True


class ActivityReport(BaseModel):
    """活动报告"""
    activity_id: str = Field(..., alias="activityId", description="活动ID")
    activity_name: str = Field(..., alias="activityName", description="活动名称")
    created_at: datetime = Field(..., alias="createdAt", description="创建时间")
    started_at: Optional[datetime] = Field(
        None, alias="startedAt", description="开始时间")
    ended_at: Optional[datetime] = Field(
        None, alias="endedAt", description="结束时间")
    summary: ActivitySummary = Field(..., description="活动摘要")
    debate_results: List[DebateResult] = Field(
        ..., alias="debateResults", description="辩题结果")
    generated_at: datetime = Field(...,
                                   alias="generatedAt", description="报告生成时间")

    class Config:
        populate_by_name = True


class ExportType(str, Enum):
    """导出数据类型"""
    VOTES = "votes"
    CHANGES = "changes"
    TIMELINE = "timeline"
    ALL = "all"
