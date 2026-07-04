from pydantic import BaseModel, Field, Field as PydanticField
from typing import Optional, List
from datetime import datetime  # 修改为 datetime 而不是 date
from app.utils.datetime_utils import TimeZoneAwareModel


class MerchantCreate(BaseModel):
    name: str = Field(..., max_length=200)
    address: Optional[str] = Field(None, max_length=500)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    is_open: Optional[bool] = Field(True)


class MerchantUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    address: Optional[str] = Field(None, max_length=500)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    is_open: Optional[bool] = Field(None)


class MerchantResponse(TimeZoneAwareModel):
    id: int
    name: str
    address: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    is_open: bool
    created_at: datetime  # 修改为 datetime 类型
    pending_proposal: Optional[dict] = None

    class Config:
        from_attributes = True


class MerchantCoordinateResponse(BaseModel):
    """商家坐标轻量响应（供地图 fitBounds 用，不分页）。"""

    id: int
    latitude: float
    longitude: float
    is_open: bool


class ProductOrderCreate(BaseModel):
    """保存每日排序记录的请求体。"""

    product_ids: list[int] = Field(..., min_length=1, description="本次保存的商品 ID 列表（按页面显示顺序）")
    session_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="按用户时区的会话日期 YYYY-MM-DD")
