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
    checked_in: bool = Field(default=False, alias="checkedIn", description="是否已入场")
    checked_in_at: Optional[datetime] = Field(None, alias="checkedInAt", description="入场时间")
    device_fingerprint: Optional[str] = Field(None, alias="deviceFingerprint", description="设备指纹")
    created_at: datetime = Field(..., alias="createdAt", description="创建时间")

    class Config:
        from_attributes = True
        populate_by_name = True


class ParticipantEnter(BaseModel):
    activity_id: str = Field(..., alias="activityId", description="活动ID")
    participant_code: str = Field(..., alias="participantCode", description="参与者编号")
    device_fingerprint: Optional[str] = Field(None, alias="deviceFingerprint", description="设备指纹")
    
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


class VoteStatus(BaseModel):
    has_voted: bool = Field(default=False, alias="hasVoted", description="是否已投票")
    position: Optional[VotePosition] = Field(None, description="投票立场")
    voted_at: Optional[datetime] = Field(None, alias="votedAt", description="投票时间")
    remaining_changes: int = Field(default=0, alias="remainingChanges", description="剩余改票次数")
    can_vote: bool = Field(default=False, alias="canVote", description="是否可以投票")
    can_change: bool = Field(default=False, alias="canChange", description="是否可以改票")
    
    class Config:
        populate_by_name = True


class VoteResults(BaseModel):
    debate_id: str = Field(..., alias="debateId", description="辩题ID")
    total_votes: int = Field(default=0, alias="totalVotes", description="总投票数")
    pro_votes: int = Field(default=0, alias="proVotes", description="正方票数")
    con_votes: int = Field(default=0, alias="conVotes", description="反方票数")
    abstain_votes: int = Field(default=0, alias="abstainVotes", description="弃权票数")
    pro_percentage: float = Field(default=0.0, alias="proPercentage", description="正方得票率")
    con_percentage: float = Field(default=0.0, alias="conPercentage", description="反方得票率")
    abstain_percentage: float = Field(default=0.0, alias="abstainPercentage", description="弃权率")
    
    class Config:
        populate_by_name = True
    winner: Optional[str] = Field(None, description="获胜方")
    is_locked: bool = Field(default=False, description="结果是否已锁定")
    locked_at: Optional[datetime] = Field(None, description="锁定时间")
