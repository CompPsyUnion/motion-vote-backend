from src.schemas.debate import DebateResponse
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ActivityStatus(str, Enum):
    upcoming = "upcoming"
    ongoing = "ongoing"
    ended = "ended"


class ActivitySettings(BaseModel):
    allowVoteChange: bool = Field(
        default=True, description="是否允许改票", alias="allow_vote_change")
    maxVoteChanges: int = Field(
        default=3, description="最大改票次数", alias="max_vote_changes")
    showRealTimeResults: bool = Field(
        default=True, description="是否显示实时结果", alias="show_real_time_results")
    requireCheckIn: bool = Field(
        default=True, description="是否需要入场验证", alias="require_check_in")
    anonymousVoting: bool = Field(
        default=True, description="是否匿名投票", alias="anonymous_voting")
    autoLockVotes: bool = Field(
        default=False, description="是否自动锁定投票", alias="auto_lock_votes")
    lockVoteDelay: int = Field(
        default=300, description="锁定投票延迟时间（秒）", alias="lock_vote_delay")

    class Config:
        populate_by_name = True


class ActivityBase(BaseModel):
    name: str = Field(..., description="活动名称")
    startTime: datetime = Field(..., description="开始时间", alias="start_time")
    endTime: datetime = Field(..., description="结束时间", alias="end_time")
    location: str = Field(..., description="活动地点")
    description: str = Field(..., description="活动描述")
    coverImage: Optional[str] = Field(
        None, description="封面图片URL", alias="cover_image")
    expectedParticipants: Optional[int] = Field(
        None, description="预计参与人数", alias="expected_participants")
    tags: Optional[List[str]] = Field(default=[], description="活动标签")
    settings: Optional[ActivitySettings] = Field(
        default_factory=ActivitySettings, description="活动设置")

    class Config:
        populate_by_name = True


class ActivityCreate(ActivityBase):
    pass


class ActivityUpdate(BaseModel):
    name: Optional[str] = Field(None, description="活动名称")
    startTime: Optional[datetime] = Field(
        None, description="开始时间", alias="start_time")
    endTime: Optional[datetime] = Field(
        None, description="结束时间", alias="end_time")
    location: Optional[str] = Field(None, description="活动地点")
    description: Optional[str] = Field(None, description="活动描述")
    coverImage: Optional[str] = Field(
        None, description="封面图片URL", alias="cover_image")
    expectedParticipants: Optional[int] = Field(
        None, description="预计参与人数", alias="expected_participants")
    tags: Optional[List[str]] = Field(None, description="活动标签")
    settings: Optional[ActivitySettings] = Field(None, description="活动设置")

    class Config:
        populate_by_name = True


class ActivityResponse(ActivityBase):
    id: str = Field(..., description="活动ID")
    status: str = Field(..., description="活动状态")
    actualParticipants: int = Field(
        default=0, description="实际参与人数", alias="actual_participants")
    ownerId: str = Field(..., description="创建者ID", alias="owner_id")
    createdAt: datetime = Field(..., description="创建时间", alias="created_at")
    updatedAt: datetime = Field(..., description="更新时间", alias="updated_at")

    class Config(ActivityBase.Config):
        from_attributes = True
        use_enum_values = True


# 添加详细的活动响应模式，包含协作者和辩题信息
class ActivityDetailStatistics(BaseModel):
    total_participants: int = Field(..., description="总参与人数")
    checked_in_participants: int = Field(..., description="已入场人数")
    total_votes: int = Field(..., description="总投票数")
    total_debates: int = Field(..., description="辩题总数")


class ActivityDetail(ActivityResponse):
    """活动详细信息，包含相关数据"""
    collaborators: List['CollaboratorResponse'] = Field(
        default=[], description="协作者列表")
    debates: List['DebateResponse'] = Field(default=[], description="辩题列表")
    currentDebate: Optional['DebateResponse'] = Field(
        None, description="当前辩题", alias="current_debate")
    statistics: ActivityDetailStatistics = Field(..., description="活动统计")

    class Config(ActivityResponse.Config):
        use_enum_values = True
        pass


class CollaboratorPermission(str, Enum):
    view = "view"
    edit = "edit"
    control = "control"


class CollaboratorStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    declined = "declined"


class CollaboratorInvite(BaseModel):
    email: str = Field(..., description="被邀请用户邮箱")
    permissions: List[CollaboratorPermission] = Field(..., description="权限列表")


class CollaboratorUpdate(BaseModel):
    permissions: List[CollaboratorPermission] = Field(..., description="权限列表")


class UserInfo(BaseModel):
    """用户基本信息"""
    id: str = Field(..., description="用户ID")
    name: str = Field(..., description="用户姓名")
    email: str = Field(..., description="用户邮箱")
    avatar: Optional[str] = Field(None, description="用户头像")

    class Config:
        from_attributes = True


class CollaboratorResponse(BaseModel):
    id: str = Field(..., description="协作者ID")
    user: UserInfo = Field(..., description="用户信息")
    permissions: List[CollaboratorPermission] = Field(..., description="权限列表")
    status: CollaboratorStatus = Field(..., description="邀请状态")
    invited_at: datetime = Field(..., description="邀请时间")
    accepted_at: Optional[datetime] = Field(None, description="接受时间")

    class Config:
        from_attributes = True


class PaginatedActivities(BaseModel):
    items: List[ActivityResponse] = Field(..., description="活动列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    limit: int = Field(..., description="每页数量")
    total_pages: int = Field(..., description="总页数")


# 导入辩题相关的 Schema（避免循环导入）

# 更新 forward references
ActivityDetail.model_rebuild()
CollaboratorResponse.model_rebuild()
