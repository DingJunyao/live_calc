from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
from app.utils.datetime_utils import TimeZoneAwareModel


KindType = Literal["home", "work", "custom"]


class UserPlaceCreate(BaseModel):
    name: str = Field(..., max_length=50)
    kind: KindType = "custom"
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    address: Optional[str] = Field(None, max_length=255)
    is_default: Optional[bool] = False
    sort_order: Optional[int] = 0
    view_radius_km: Optional[float] = Field(5, ge=0.5, le=100)


class UserPlaceUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=50)
    kind: Optional[KindType] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    address: Optional[str] = Field(None, max_length=255)
    sort_order: Optional[int] = None
    view_radius_km: Optional[float] = Field(None, ge=0.5, le=100)


class UserPlaceResponse(TimeZoneAwareModel):
    id: int
    name: str
    kind: str
    latitude: float
    longitude: float
    address: Optional[str]
    is_default: bool
    sort_order: int
    view_radius_km: float
    created_at: datetime

    class Config:
        from_attributes = True
