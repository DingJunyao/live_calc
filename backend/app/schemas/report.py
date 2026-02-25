from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import date
from decimal import Decimal


class ExpenseCreate(BaseModel):
    type: str  # water, gas, electricity, transport
    amount: Decimal = Field(..., gt=0)
    unit: Optional[str] = None
    date: date
    notes: Optional[str] = Field(None, max_length=500)


class ExpenseResponse(BaseModel):
    id: int
    type: str
    amount: Decimal
    unit: Optional[str]
    date: date
    notes: Optional[str]

    class Config:
        from_attributes = True


class ReportRequest(BaseModel):
    start_date: date
    end_date: date
    category: str = "all"  # all, food, transport, utility
    granularity: str = "daily"  # daily, weekly, monthly


class ExpenseReportResponse(BaseModel):
    total_expense: Decimal
    currency: str
    category_breakdown: Dict[str, Decimal]
    time_series: List[Dict]


class PriceTrendResponse(BaseModel):
    product_name: str
    time_series: List[Dict]
