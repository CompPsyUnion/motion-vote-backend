from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1, description="页码")
    limit: int = Field(default=20, ge=1, le=100, description="每页数量")


class PaginatedResponse(BaseModel):
    items: List[Any] = Field(..., description="数据列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    limit: int = Field(..., description="每页数量")
    total_pages: int = Field(..., description="总页数")


class ApiResponse(BaseModel):
    success: bool = Field(default=True, description="请求是否成功")
    message: str = Field(..., description="响应消息")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="响应时间戳")


class ErrorResponse(BaseModel):
    success: bool = Field(default=False, description="请求是否成功")
    message: str = Field(..., description="错误消息")
    code: str = Field(..., description="错误代码")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="错误时间戳")


class FileUploadResponse(BaseModel):
    filename: str = Field(..., description="文件名")
    url: str = Field(..., description="文件URL")
    size: int = Field(..., description="文件大小")


class BatchImportResult(BaseModel):
    success_count: int = Field(..., description="成功导入数量")
    error_count: int = Field(..., description="失败数量")
    errors: List[Dict[str, Any]] = Field(default=[], description="错误详情")
    total: int = Field(..., description="总数量")
