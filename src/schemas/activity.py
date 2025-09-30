from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class ActivityStatus(str, Enum):
    upcoming = "upcoming"
    ongoing = "ongoing"
    ended = "ended"


class ActivitySettings(BaseModel):
    allow_vote_change: bool = Field(default=True, description="是否允许改票")
    max_vote_changes: int = Field(default=3, description="最大改票次数")
    show_real_time_results: bool = Field(default=True, description="是否显示实时结果")
    require_check_in: bool = Field(default=True, description="是否需要入场验证")
    anonymous_voting: bool = Field(default=True, description="是否匿名投票")
    auto_lock_votes: bool = Field(default=False, description="是否自动锁定投票")
    lock_vote_delay: int = Field(default=300, description="锁定投票延迟时间（秒）")


class ActivityBase(BaseModel):
    name: str = Field(..., description="活动名称")
    start_time: datetime = Field(..., description="开始时间")
    end_time: datetime = Field(..., description="结束时间")
    location: str = Field(..., description="活动地点")
    description: str = Field(..., description="活动描述")
    cover_image: Optional[str] = Field(None, description="封面图片URL")
    expected_participants: Optional[int] = Field(None, description="预计参与人数")
    tags: Optional[List[str]] = Field(default=[], description="活动标签")
    settings: Optional[ActivitySettings] = Field(
        default_factory=ActivitySettings, description="活动设置")


class ActivityCreate(ActivityBase):
    pass


class ActivityUpdate(BaseModel):
    name: Optional[str] = Field(None, description="活动名称")
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    location: Optional[str] = Field(None, description="活动地点")
    description: Optional[str] = Field(None, description="活动描述")
    cover_image: Optional[str] = Field(None, description="封面图片URL")
    expected_participants: Optional[int] = Field(None, description="预计参与人数")
    tags: Optional[List[str]] = Field(None, description="活动标签")
    settings: Optional[ActivitySettings] = Field(None, description="活动设置")


class ActivityResponse(ActivityBase):
    id: str = Field(..., description="活动ID")
    status: ActivityStatus = Field(..., description="活动状态")
    actual_participants: int = Field(default=0, description="实际参与人数")
    owner_id: str = Field(..., description="创建者ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class CollaboratorPermission(str, Enum):
    view = "view"
    edit = "edit"
    control = "control"


class CollaboratorStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    declined = "declined"


class CollaboratorInvite(BaseModel):
    email: str = Field(..., description="协作者邮箱")
    permissions: List[CollaboratorPermission] = Field(..., description="权限列表")


class CollaboratorUpdate(BaseModel):
    permissions: List[CollaboratorPermission] = Field(..., description="权限列表")


class CollaboratorResponse(BaseModel):
    id: str = Field(..., description="协作者ID")
    user_id: str = Field(..., description="用户ID")
    activity_id: str = Field(..., description="活动ID")
    permissions: List[CollaboratorPermission] = Field(..., description="权限列表")
    status: CollaboratorStatus = Field(..., description="邀请状态")
    invited_at: datetime = Field(..., description="邀请时间")
    accepted_at: Optional[datetime] = Field(None, description="接受时间")

    class Config:
        from_attributes = True
