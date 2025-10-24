from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class VotePosition(str, Enum):
    pro = "pro"
    con = "con"
    abstain = "abstain"


class ParticipantBase(BaseModel):
    code: str = Field(..., description="参与者编号")
    name: str = Field(..., description="参与者姓名")
    phone: Optional[str] = Field(None, description="手机号")
    note: Optional[str] = Field(None, description="备注")


class ParticipantCreate(ParticipantBase):
    pass


class ParticipantResponse(ParticipantBase):
    id: str = Field(..., description="参与者ID")
    activity_id: str = Field(..., alias="activityId", description="活动ID")
    checked_in: bool = Field(
        default=False, alias="checkedIn", description="是否已入场")
    checked_in_at: Optional[datetime] = Field(
        None, alias="checkedInAt", description="入场时间")
    device_fingerprint: Optional[str] = Field(
        None, alias="deviceFingerprint", description="设备指纹")
    created_at: datetime = Field(..., alias="createdAt", description="创建时间")

    class Config:
        from_attributes = True
        populate_by_name = True


class ParticipantEnter(BaseModel):
    # 方式1: 提供 activity_id 和 participant_code
    activity_id: Optional[str] = Field(
        None, alias="activityId", description="活动ID")
    participant_code: Optional[str] = Field(
        None, alias="participantCode", description="参与者编号")

    # 方式2: 直接提供 participant_id（推荐）
    participant_id: Optional[str] = Field(
        None, alias="participantId", description="参与者ID")

    device_fingerprint: Optional[str] = Field(
        None, alias="deviceFingerprint", description="设备指纹")

    class Config:
        populate_by_name = True


class ParticipantInfo(BaseModel):
    id: str = Field(..., description="参与者ID")
    code: str = Field(..., description="参与者编号")
    name: str = Field(..., description="参与者姓名")


class ActivityInfo(BaseModel):
    id: str = Field(..., description="活动ID")
    name: str = Field(..., description="活动名称")
    status: str = Field(..., description="活动状态")


class VoteRequest(BaseModel):
    session_token: str = Field(..., alias="sessionToken", description="会话令牌")
    position: VotePosition = Field(..., description="投票立场")

    class Config:
        populate_by_name = True


class ParticipantVoteStatus(BaseModel):
    has_voted: bool = Field(
        default=False, alias="hasVoted", description="是否已投票")
    position: Optional[VotePosition] = Field(None, description="投票立场")
    voted_at: Optional[datetime] = Field(
        None, alias="votedAt", description="投票时间")
    remaining_changes: int = Field(
        default=0, alias="remainingChanges", description="剩余改票次数")
    can_vote: bool = Field(
        default=False, alias="canVote", description="是否可以投票")
    can_change: bool = Field(
        default=False, alias="canChange", description="是否可以改票")

    class Config:
        populate_by_name = True


class VoteStats(BaseModel):
    debate_id: str = Field(..., alias="debateId", description="辩题ID")
    total_votes: int = Field(default=0, alias="totalVotes", description="总投票数")
    pro_votes: int = Field(default=0, alias="proVotes", description="正方最终票数")
    pro_previous_votes: int = Field(
        default=0, alias="proPreviousVotes", description="正方初始票数")
    pro_to_con_votes: int = Field(
        default=0, alias="proToConVotes", description="正方到反方票数")
    con_votes: int = Field(default=0, alias="conVotes", description="反方最终票数")
    con_previous_votes: int = Field(
        default=0, alias="conPreviousVotes", description="反方初始票数")
    con_to_pro_votes: int = Field(
        default=0, alias="conToProVotes", description="反方到正方票数")
    abstain_votes: int = Field(
        default=0, alias="abstainVotes", description="中立最终票数")
    abstain_previous_votes: int = Field(
        default=0, alias="abstainPreviousVotes", description="中立初始票数")
    abstain_to_pro_votes: int = Field(
        default=0, alias="abstainToProVotes", description="中立到正方票数")
    abstain_to_con_votes: int = Field(
        default=0, alias="abstainToConVotes", description="中立到反方票数")
    pro_score: float = Field(default=0.0, alias="proScore", description="正方分数")
    con_score: float = Field(default=0.0, alias="conScore", description="反方分数")
    abstain_percentage: float = Field(
        default=0.0, alias="abstainPercentage", description="弃权率")
    winner: Optional[str] = Field(None, description="获胜方")
    is_locked: bool = Field(
        default=False, alias="isLocked", description="结果是否已锁定")
    locked_at: Optional[datetime] = Field(
        None, alias="lockedAt", description="锁定时间")

    class Config:
        populate_by_name = True
