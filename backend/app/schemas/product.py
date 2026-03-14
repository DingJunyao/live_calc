from pydantic import BaseModel, Field, field_serializer
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class ProductRecordCreate(BaseModel):
    product_id: Optional[int] = None  # 可选，如果不提供则自动创建商品
    product_name: Optional[str] = Field(None, max_length=200)  # 可选，如果提供 product_id 则不需要
    merchant_id: Optional[int] = None
    price: Decimal = Field(..., gt=0, decimal_places=2)
    currency: str = "CNY"
    original_quantity: Decimal = Field(..., gt=0)
    original_unit: str
    record_type: str = "purchase"
    notes: Optional[str] = Field(None, max_length=500)
    recorded_at: Optional[datetime] = None  # 这个SB字段用于自定义记录时间


class ProductRecordUpdate(BaseModel):
    merchant_id: Optional[int] = None
    price: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    currency: Optional[str] = "CNY"
    original_quantity: Optional[Decimal] = Field(None, gt=0)
    original_unit: Optional[str] = None
    record_type: Optional[str] = None
    notes: Optional[str] = Field(None, max_length=500)
    recorded_at: Optional[datetime] = None


class ProductRecordResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    merchant_id: Optional[int]
    merchant_name: Optional[str]  # 商家名称
    price: Decimal
    currency: str
    original_quantity: Decimal
    original_unit: str  # 单位缩写字符串
    standard_quantity: Decimal
    standard_unit: str  # 标准单位缩写字符串
    record_type: str
    exchange_rate: Decimal
    recorded_at: datetime
    notes: Optional[str]

    class Config:
        from_attributes = False  # 手动构造响应，不从模型自动读取


class ProductHistoryResponse(BaseModel):
    product_name: str
    records: List[ProductRecordResponse]
