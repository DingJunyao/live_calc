from pydantic import BaseModel, Decimal
from typing import Optional, List


class NutritionDataResponse(BaseModel):
    id: int
    usda_id: str
    name_en: str
    name_zh: Optional[str]
    calories: Optional[Decimal]
    protein: Optional[Decimal]
    fat: Optional[Decimal]
    carbs: Optional[Decimal]
    fiber: Optional[Decimal]
    sugar: Optional[Decimal]
    sodium: Optional[Decimal]

    class Config:
        from_attributes = True


class IngredientMatch(BaseModel):
    nutrition_id: int
    name_en: str
    name_zh: Optional[str]
    confidence: Decimal


class NutritionMatchResponse(BaseModel):
    matches: List[IngredientMatch]


class NutritionCorrectRequest(BaseModel):
    ingredient_name: str
    nutrition_id: int
