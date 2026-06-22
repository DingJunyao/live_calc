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

    class Config:
        from_attributes = True


class MerchantCoordinateResponse(BaseModel):
    """商家坐标轻量响应（供地图 fitBounds 用，不分页）。"""

    id: int
    latitude: float
    longitude: float
    is_open: bool
