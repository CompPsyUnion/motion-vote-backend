from typing import Optional

from pydantic import BaseModel, Field


class SiteInfoBase(BaseModel):
    title: str = Field(..., description="站点名称/标题")
    description: Optional[str] = Field(None, description="描述")
    open_register: bool = Field(True, description="开放注册")
    icon: Optional[str] = Field(None, description="图标URL")
    contact: Optional[str] = Field(None, description="联系方式跳转链接")
    icp: Optional[str] = Field(None, description="ICP备案号")
    footer_text: Optional[str] = Field(None, description="脚部文本")


class SiteInfoCreate(SiteInfoBase):
    pass


class SiteInfoUpdate(BaseModel):
    title: Optional[str] = Field(None, description="站点名称/标题")
    description: Optional[str] = Field(None, description="描述")
    open_register: Optional[bool] = Field(None, description="开放注册")
    icon: Optional[str] = Field(None, description="图标URL")
    contact: Optional[str] = Field(None, description="联系方式跳转链接")
    icp: Optional[str] = Field(None, description="ICP备案号")
    footer_text: Optional[str] = Field(None, description="脚部文本")


class SiteInfoResponse(SiteInfoBase):
    class Config:
        from_attributes = True
