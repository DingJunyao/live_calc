from pydantic import BaseModel, Field, Field as PydanticField
from typing import Optional, List
from datetime import date


class LocationCreate(BaseModel):
    name: str = Field(..., max_length=200)
    address: Optional[str] = Field(None, max_length=500)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)


class LocationResponse(BaseModel):
    id: int
    name: str
    address: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    created_at: date

    class Config:
        from_attributes = True


class FavoriteLocationCreate(BaseModel):
    name: str = Field(..., max_length=200)
    type: str = "other"
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class FavoriteLocationResponse(BaseModel):
    id: int
    name: str
    type: str
    latitude: float
    longitude: float
    created_at: date

    class Config:
        from_attributes = True


class RouteCalculateRequest(BaseModel):
    from_location_id: int
    to_location_id: int
    travel_mode: str = "driving"  # driving, walking, cycling, transit
    map_provider: str = "amap"


class RouteCalculateResponse(BaseModel):
    distance: float  # 公里
    duration: int  # 分钟
    cost: float  # 成本
    currency: str
