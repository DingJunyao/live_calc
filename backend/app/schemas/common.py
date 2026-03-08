"""通用数据模式定义"""
from typing import Generic, TypeVar, List, Optional
from pydantic import BaseModel, Field

T = TypeVar('T')


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应模型"""
    items: List[T] = Field(..., description="数据项列表")
    total: int = Field(..., description="总数据量")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页显示数量")
    total_pages: int = Field(..., description="总页数")

    @classmethod
    def create(cls, items: List[T], total: int, page: int, page_size: int):
        """创建分页响应"""
        total_pages = (total + page_size - 1) // page_size
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )


class MessageResponse(BaseModel):
    """通用消息响应"""
    message: str = Field(..., description="消息内容")
    success: bool = Field(default=True, description="是否成功")
