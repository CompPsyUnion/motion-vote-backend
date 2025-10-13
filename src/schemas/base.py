from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1, description="页码")
    limit: int = Field(default=20, ge=1, le=100, description="每页数量")


class PaginatedResponse(BaseModel):
    items: List[Any] = Field(..., description="数据列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    limit: int = Field(..., description="每页数量")
    total_pages: int = Field(..., alias="totalPages", description="总页数")

    class Config:
        populate_by_name = True


class ApiResponse(BaseModel):
    success: bool = Field(default=True, description="请求是否成功")
    message: str = Field(..., description="响应消息")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="响应时间戳")
    data: Optional[Any] = Field(None, description="响应数据")

    class Config:
        populate_by_name = True


class ErrorResponse(BaseModel):
    success: bool = Field(default=False, description="请求是否成功")
    message: str = Field(..., description="错误消息")
    code: str = Field(..., description="错误代码")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="错误时间戳")


class FileUploadResponse(BaseModel):
    filename: str = Field(..., description="文件名")
    url: str = Field(..., description="文件URL")
    size: int = Field(..., description="文件大小")

    class Config:
        populate_by_name = True


class BatchImportResult(BaseModel):
    success_count: int = Field(..., alias="successCount", description="成功导入数量")
    error_count: int = Field(..., alias="errorCount", description="失败数量")
    errors: List[Dict[str, Any]] = Field(default=[], description="错误详情")
    total: int = Field(..., description="总数量")

    class Config:
        populate_by_name = True
