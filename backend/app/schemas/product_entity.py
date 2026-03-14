from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from app.utils.database_helpers import validate_tags


class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    brand: Optional[str] = Field(None, max_length=100)
    barcode: Optional[str] = Field(None, max_length=50)
    image_url: Optional[str] = Field(None, max_length=500)
    ingredient_id: int
    tags: List[str] = Field(default_factory=list)

    @field_validator('tags')
    @classmethod
    def validate_tags_list(cls, v):
        return validate_tags(v) if v else []


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    brand: Optional[str] = Field(None, max_length=100)
    barcode: Optional[str] = Field(None, max_length=50)
    image_url: Optional[str] = Field(None, max_length=500)
    ingredient_id: Optional[int] = None
    tags: Optional[List[str]] = None


class ProductResponse(ProductBase):
    id: int
    ingredient_name: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime]
    is_active: bool

    class Config:
        from_attributes = True


class ProductWithDetails(ProductResponse):
    ingredient_name: Optional[str] = None
    latest_price: Optional[float] = None
    latest_price_date: Optional[datetime] = None


# ==================== 条码相关 Schema ====================

class ProductBarcodeBase(BaseModel):
    barcode: str = Field(..., min_length=1, max_length=50)
    barcode_type: str = Field(default="internal", max_length=20)
    is_primary: bool = False


class ProductBarcodeCreate(ProductBarcodeBase):
    product_id: int


class ProductBarcodeUpdate(BaseModel):
    is_primary: Optional[bool] = None
    is_active: Optional[bool] = None


class ProductBarcodeResponse(ProductBarcodeBase):
    id: int
    product_id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
