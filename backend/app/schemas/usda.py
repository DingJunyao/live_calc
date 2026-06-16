# backend/app/schemas/usda.py
from pydantic import BaseModel


class UsdaSearchItem(BaseModel):
    fdc_id: int
    description: str | None = None
    description_zh: str | None = None
    data_type: str | None = None
    nutrient_count: int = 0
    score: int = 0


class UsdaNutrientItem(BaseModel):
    name: str
    name_zh: str | None = None
    amount: float
    unit_name: str


class UsdaFoodDetail(BaseModel):
    fdc_id: int
    description: str | None = None
    description_zh: str | None = None
    data_type: str | None = None
    nutrients: list[UsdaNutrientItem] = []


class UsdaMatchRequest(BaseModel):
    fdc_id: int
