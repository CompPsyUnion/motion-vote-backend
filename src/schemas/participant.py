from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ParticipantBase(BaseModel):
    name: str = Field(..., description="参与者姓名")
    phone: Optional[str] = Field(None, description="手机号")
    note: Optional[str] = Field(None, description="备注")


class ParticipantCreate(ParticipantBase):
    """创建参与者的数据模型"""
    pass


class ParticipantResponse(ParticipantBase):
    """参与者响应数据模型"""
    id: str = Field(..., description="参与者ID")
    activity_id: str = Field(..., alias="activityId", description="活动ID")
    code: str = Field(..., description="参与者编号")
    checked_in: bool = Field(..., alias="checkedIn", description="是否已入场")
    checked_in_at: Optional[datetime] = Field(None, alias="checkedInAt", description="入场时间")
    device_fingerprint: Optional[str] = Field(None, alias="deviceFingerprint", description="设备指纹")
    created_at: datetime = Field(..., alias="createdAt", description="创建时间")

    class Config:
        from_attributes = True
        populate_by_name = True


class ParticipantUpdate(BaseModel):
    """更新参与者信息"""
    name: Optional[str] = Field(None, description="参与者姓名")
    phone: Optional[str] = Field(None, description="手机号")
    note: Optional[str] = Field(None, description="备注")


class PaginatedParticipants(BaseModel):
    """分页参与者列表"""
    items: List[ParticipantResponse] = Field(..., description="参与者列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    limit: int = Field(..., description="每页数量")
    total_pages: int = Field(..., alias="totalPages", description="总页数")
    
    class Config:
        populate_by_name = True


class ParticipantBatchImportResult(BaseModel):
    """批量导入结果"""
    total: int = Field(..., description="总数量")
    success: int = Field(..., description="成功数量")
    failed: int = Field(..., description="失败数量")
    errors: List[str] = Field(..., description="错误信息")
    
    class Config:
        populate_by_name = True


class ParticipantInfo(BaseModel):
    """参与者基本信息"""
    id: str = Field(..., description="参与者ID")
    code: str = Field(..., description="参与者编号")
    name: str = Field(..., description="参与者姓名")

    class Config:
        from_attributes = True


class ParticipantEnter(BaseModel):
    """参与者入场请求"""
    activity_id: str = Field(..., alias="activityId", description="活动ID")
    participant_code: str = Field(..., alias="participantCode", description="参与者编号")
    device_fingerprint: Optional[str] = Field(None, alias="deviceFingerprint", description="设备指纹")
    
    class Config:
        populate_by_name = True  # 允许同时使用字段名和别名


class ParticipantLinksResponse(BaseModel):
    """参与者链接响应"""
    participant_info: ParticipantInfo = Field(..., alias="participantInfo", description="参与者信息")
    check_in_link: str = Field(..., alias="checkInLink", description="签到链接")
    vote_link: str = Field(..., alias="voteLink", description="投票链接")
    
    class Config:
        populate_by_name = True