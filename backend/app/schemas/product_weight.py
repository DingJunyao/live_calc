from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ProductWeightOverrideBase(BaseModel):
    weight: int = Field(default=50, ge=0, le=100)


class ProductWeightOverrideCreate(ProductWeightOverrideBase):
    pass


class ProductWeightOverrideUpdate(BaseModel):
    weight: Optional[int] = Field(None, ge=0, le=100)


class ProductWeightOverrideResponse(ProductWeightOverrideBase):
    id: int
    user_id: int
    product_id: int
    created_at: datetime
    updated_at: Optional[datetime]
    is_active: bool

    class Config:
        from_attributes = True


class EffectiveWeightResponse(BaseModel):
    """返回某商品对当前用户的生效权重 + 来源。"""
    product_id: int
    effective_weight: int
    global_weight: int
    override_weight: Optional[int] = None
    source: str  # "override" | "global"
